import os
import logging
from flask import render_template, url_for, flash, redirect, request, jsonify, send_file, g
from flask_login import login_user, current_user, logout_user, login_required
from urllib.parse import urlparse
from datetime import datetime, timedelta
import tempfile

from app import app, db
from models import User, PortfolioItem, WatchlistItem, PortfolioHistory
from forms import RegistrationForm, LoginForm, PortfolioItemForm, WatchlistItemForm, WatchlistNoteForm, ReportGeneratorForm
from stock_utils import get_stock_price, get_stock_history, get_stock_symbols, get_daily_change
from report_generator import generate_monthly_report_pdf, generate_monthly_report_excel
from form_helpers import format_form_errors

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.context_processor
def inject_now():
    """Add current date to all templates"""
    return {'now': datetime.now()}

@app.route('/')
def index():
    """Home page route"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html', title='Investment Dashboard')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route"""
    logger.info("Register route accessed")
    if current_user.is_authenticated:
        logger.info("User already authenticated, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    logger.info(f"Request method: {request.method}")
    if form.validate_on_submit():
        logger.info(f"Form validated, username: {form.username.data}, email: {form.email.data}")
        try:
            # Create new user - ensure values aren't None
            username = form.username.data if form.username.data else ""
            email = form.email.data if form.email.data else ""
            password = form.password.data if form.password.data else ""
            
            # Input validation
            if not username or not email or not password:
                logger.warning("Missing required fields")
                flash('All fields are required', 'danger')
                return render_template('register.html', title='Register', form=form)
            
            user = User()
            user.username = username
            user.email = email
            user.set_password(password)
            
            # Add to database
            logger.info("Adding user to database...")
            db.session.add(user)
            db.session.commit()
            logger.info(f"User created successfully with id: {user.id}")
            
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            flash(f'An error occurred during registration: {str(e)}', 'danger')
    elif request.method == 'POST':
        logger.warning(f"Form validation failed. Errors: {form.errors}")
        # Use our helper function to format and display errors
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            logger.error(f"Error formatting flash messages: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    logger.info("Login route accessed")
    if current_user.is_authenticated:
        logger.info("User already authenticated, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    logger.info(f"Request method: {request.method}")
    if form.validate_on_submit():
        logger.info(f"Form validated, username: {form.username.data}")
        
        # Handle possible None values
        username = form.username.data if form.username.data else ""
        password = form.password.data if form.password.data else ""
        
        # Check for empty inputs
        if not username or not password:
            logger.warning("Missing username or password")
            flash('Both username and password are required', 'danger')
            return render_template('login.html', title='Login', form=form)
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            logger.info(f"User found: {user.username}, id: {user.id}")
            password_check = user.check_password(password)
            logger.info(f"Password check result: {password_check}")
            
            if password_check:
                logger.info("Login successful, calling login_user()")
                login_user(user)
                next_page = request.args.get('next')
                logger.info(f"Next page: {next_page}")
                
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('dashboard')
                
                logger.info(f"Redirecting to: {next_page}")
                flash('Login successful!', 'success')
                return redirect(next_page)
        
        logger.warning("Login failed - invalid username or password")
        flash('Login unsuccessful. Please check username and password.', 'danger')
    elif request.method == 'POST':
        logger.warning(f"Form validation failed. Errors: {form.errors}")
        # Use our helper function to format and display errors
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            logger.error(f"Error formatting flash messages: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    """User logout route"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard route"""
    portfolio_form = PortfolioItemForm()
    watchlist_form = WatchlistItemForm()
    
    # Get portfolio items with current prices
    portfolio_items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    portfolio_data = []
    total_investment = 0
    total_current_value = 0
    
    for item in portfolio_items:
        try:
            current_price = get_stock_price(item.symbol)
            if current_price is None:
                # Skip items with no current price data
                logger.warning(f"Unable to fetch current price for {item.symbol}")
                continue
                
            investment = item.quantity * item.buy_price
            current_value = item.quantity * current_price
            gain_loss = current_value - investment
            gain_loss_percent = (gain_loss / investment) * 100 if investment > 0 else 0
            
            total_investment += investment
            total_current_value += current_value
            
            portfolio_data.append({
                'id': item.id,
                'symbol': item.symbol,
                'quantity': item.quantity,
                'buy_price': item.buy_price,
                'exchange': item.exchange,
                'current_price': current_price,
                'investment': investment,
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent
            })
        except Exception as e:
            logger.error(f"Error processing portfolio item {item.symbol}: {str(e)}")
    
    # Calculate total gain/loss
    total_gain_loss = total_current_value - total_investment
    total_gain_loss_percent = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
    
    # Save portfolio history for today if not already saved
    today = datetime.now().date()
    existing_history = PortfolioHistory.query.filter_by(
        user_id=current_user.id, 
        date=today
    ).first()
    
    if not existing_history and total_current_value > 0:
        # Get yesterday's record if available to calculate daily change
        yesterday = today - timedelta(days=1)
        yesterday_history = PortfolioHistory.query.filter_by(
            user_id=current_user.id,
            date=yesterday
        ).first()
        
        daily_change = 0
        daily_change_percent = 0
        
        if yesterday_history:
            daily_change = total_current_value - yesterday_history.total_value
            daily_change_percent = (daily_change / yesterday_history.total_value) * 100 if yesterday_history.total_value > 0 else 0
        
        try:
            portfolio_history = PortfolioHistory(
                user_id=current_user.id,
                date=today,
                total_value=total_current_value,
                daily_change=daily_change,
                daily_change_percent=daily_change_percent
            )
            db.session.add(portfolio_history)
            db.session.commit()
            logger.info(f"Saved portfolio history for {today}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving portfolio history: {str(e)}")
    
    # Get performance history for chart
    history_data = PortfolioHistory.query.filter_by(user_id=current_user.id)\
        .order_by(PortfolioHistory.date).all()
    
    # Initialize with empty lists in case there's no data yet
    dates = []
    values = []
    daily_changes = []
    
    # Format the data for the chart
    for h in history_data:
        if h.date:
            dates.append(h.date.strftime('%Y-%m-%d'))
        else:
            dates.append('')
            
        if h.total_value is not None:
            # Ensure we have a plain Python float, not a SQLAlchemy or decimal type
            values.append(float(h.total_value))
        else:
            values.append(0.0)
            
        if h.daily_change_percent is not None:
            # Ensure we have a plain Python float
            daily_changes.append(float(h.daily_change_percent))
        else:
            daily_changes.append(0.0)
    
    # Create a data structure for the charts that is JSON serializable
    performance_data = {
        'dates': dates,
        'values': values,
        'daily_changes': daily_changes
    }
    
    # Get watchlist items
    watchlist_items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    watchlist_data = []
    
    for item in watchlist_items:
        try:
            current_price = get_stock_price(item.symbol)
            if current_price is None:
                continue
                
            daily_change, daily_change_percent = get_daily_change(item.symbol)
            
            watchlist_data.append({
                'id': item.id,
                'symbol': item.symbol,
                'exchange': item.exchange,
                'notes': item.notes,
                'current_price': current_price,
                'daily_change': daily_change,
                'daily_change_percent': daily_change_percent
            })
        except Exception as e:
            logger.error(f"Error processing watchlist item {item.symbol}: {str(e)}")
    
    return render_template(
        'dashboard.html', 
        title='Dashboard',
        portfolio_form=portfolio_form,
        watchlist_form=watchlist_form,
        portfolio_data=portfolio_data,
        total_investment=total_investment,
        total_current_value=total_current_value,
        total_gain_loss=total_gain_loss,
        total_gain_loss_percent=total_gain_loss_percent,
        performance_data=performance_data,
        watchlist_data=watchlist_data
    )

@app.route('/portfolio')
@login_required
def portfolio():
    """Portfolio page route"""
    portfolio_form = PortfolioItemForm()
    
    # Get portfolio items with current prices
    portfolio_items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    portfolio_data = []
    total_investment = 0
    total_current_value = 0
    
    for item in portfolio_items:
        try:
            current_price = get_stock_price(item.symbol)
            if current_price is None:
                # Skip items with no current price data
                logger.warning(f"Unable to fetch current price for {item.symbol}")
                continue
                
            investment = item.quantity * item.buy_price
            current_value = item.quantity * current_price
            gain_loss = current_value - investment
            gain_loss_percent = (gain_loss / investment) * 100 if investment > 0 else 0
            
            total_investment += investment
            total_current_value += current_value
            
            portfolio_data.append({
                'id': item.id,
                'symbol': item.symbol,
                'quantity': item.quantity,
                'buy_price': item.buy_price,
                'exchange': item.exchange,
                'current_price': current_price,
                'investment': investment,
                'current_value': current_value,
                'gain_loss': gain_loss,
                'gain_loss_percent': gain_loss_percent
            })
        except Exception as e:
            logger.error(f"Error processing portfolio item {item.symbol}: {str(e)}")
    
    # Calculate total gain/loss
    total_gain_loss = total_current_value - total_investment
    total_gain_loss_percent = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
    
    return render_template(
        'portfolio.html', 
        title='My Portfolio',
        portfolio_form=portfolio_form,
        portfolio_data=portfolio_data,
        total_investment=total_investment,
        total_current_value=total_current_value,
        total_gain_loss=total_gain_loss,
        total_gain_loss_percent=total_gain_loss_percent
    )

@app.route('/watchlist')
@login_required
def watchlist():
    """Watchlist page route"""
    watchlist_form = WatchlistItemForm()
    
    # Get watchlist items
    watchlist_items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    watchlist_data = []
    
    for item in watchlist_items:
        try:
            current_price = get_stock_price(item.symbol)
            if current_price is None:
                continue
                
            daily_change, daily_change_percent = get_daily_change(item.symbol)
            
            watchlist_data.append({
                'id': item.id,
                'symbol': item.symbol,
                'exchange': item.exchange,
                'notes': item.notes,
                'current_price': current_price,
                'daily_change': daily_change,
                'daily_change_percent': daily_change_percent
            })
        except Exception as e:
            logger.error(f"Error processing watchlist item {item.symbol}: {str(e)}")
    
    return render_template(
        'watchlist.html', 
        title='My Watchlist',
        watchlist_form=watchlist_form,
        watchlist_data=watchlist_data
    )

@app.route('/portfolio/add', methods=['POST'])
@login_required
def add_portfolio_item():
    """Add a new item to user's portfolio"""
    form = PortfolioItemForm()
    if form.validate_on_submit():
        # Get form data with null checks
        symbol = form.symbol.data if form.symbol.data else ""
        
        # Validate required fields
        if not symbol:
            flash("Stock symbol is required", "danger")
            return redirect(url_for('dashboard'))
            
        try:
            # Check if stock symbol is valid
            logger.info(f"Validating stock symbol: {symbol}")
            current_price = get_stock_price(symbol)
            if current_price is None:
                flash(f"Invalid stock symbol: {symbol}. Please check and try again.", "danger")
                return redirect(url_for('dashboard'))
                
            # Get remaining form data
            quantity = form.quantity.data if form.quantity.data is not None else 0
            
            # Explicitly handle buy_price - this is a key fix for the form validation issue
            if form.buy_price.data is None:
                flash("Buy price is required", "danger")
                return redirect(url_for('dashboard'))
                
            buy_price = float(form.buy_price.data)
            exchange = form.exchange.data if form.exchange.data else "NSE"
            
            # Validate the buy price
            if buy_price <= 0:
                flash("Buy price must be greater than zero", "danger")
                return redirect(url_for('dashboard'))
            
            # Add the portfolio item
            logger.info(f"Creating portfolio item: {symbol}, {quantity}, {buy_price}, {exchange}")
            portfolio_item = PortfolioItem(
                symbol=symbol,
                quantity=quantity,
                buy_price=buy_price,
                exchange=exchange,
                user_id=current_user.id
            )
            db.session.add(portfolio_item)
            db.session.commit()
            
            flash(f"{symbol} added to your portfolio successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding portfolio item: {str(e)}")
            flash(f"Error adding item to portfolio: {str(e)}", "danger")
    else:
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            logger.error(f"Error formatting form errors: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return redirect(url_for('dashboard'))

@app.route('/portfolio/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_portfolio_item(item_id):
    """Delete a portfolio item"""
    item = PortfolioItem.query.get_or_404(item_id)
    
    # Check if the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to delete this item", "danger")
        return redirect(url_for('dashboard'))
    
    try:
        symbol = item.symbol
        db.session.delete(item)
        db.session.commit()
        flash(f"{symbol} has been removed from your portfolio", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting portfolio item: {str(e)}")
        flash(f"Error removing item from portfolio: {str(e)}", "danger")
    
    return redirect(url_for('dashboard'))

@app.route('/watchlist/add', methods=['POST'])
@login_required
def add_watchlist_item():
    """Add a new item to user's watchlist"""
    form = WatchlistItemForm()
    if form.validate_on_submit():
        # Get form data with null checks
        symbol = form.symbol.data if form.symbol.data else ""
        
        # Validate required fields
        if not symbol:
            flash("Stock symbol is required", "danger")
            return redirect(url_for('dashboard'))
            
        try:
            # Check if stock symbol is valid
            logger.info(f"Validating stock symbol: {symbol}")
            current_price = get_stock_price(symbol)
            if current_price is None:
                flash(f"Invalid stock symbol: {symbol}. Please check and try again.", "danger")
                return redirect(url_for('dashboard'))
                
            # Get remaining form data
            exchange = form.exchange.data if form.exchange.data else "NSE"
            notes = form.notes.data if form.notes.data else ""
            
            # Check if item already exists in watchlist
            existing = WatchlistItem.query.filter_by(
                user_id=current_user.id,
                symbol=symbol
            ).first()
            
            if existing:
                flash(f"{symbol} is already in your watchlist", "warning")
                return redirect(url_for('dashboard'))
            
            # Add the watchlist item
            logger.info(f"Creating watchlist item: {symbol}, {exchange}")
            watchlist_item = WatchlistItem(
                symbol=symbol,
                exchange=exchange,
                notes=notes,
                user_id=current_user.id
            )
            db.session.add(watchlist_item)
            db.session.commit()
            
            flash(f"{symbol} added to your watchlist successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding watchlist item: {str(e)}")
            flash(f"Error adding item to watchlist: {str(e)}", "danger")
    else:
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            logger.error(f"Error formatting form errors: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return redirect(url_for('dashboard'))

@app.route('/watchlist/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_watchlist_item(item_id):
    """Delete a watchlist item"""
    item = WatchlistItem.query.get_or_404(item_id)
    
    # Check if the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to delete this item", "danger")
        return redirect(url_for('dashboard'))
    
    try:
        symbol = item.symbol
        db.session.delete(item)
        db.session.commit()
        flash(f"{symbol} has been removed from your watchlist", "success")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting watchlist item: {str(e)}")
        flash(f"Error removing item from watchlist: {str(e)}", "danger")
    
    return redirect(url_for('dashboard'))

@app.route('/watchlist/update/<int:item_id>', methods=['POST'])
@login_required
def update_watchlist_notes(item_id):
    """Update notes for a watchlist item"""
    item = WatchlistItem.query.get_or_404(item_id)
    
    # Check if the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to update this item", "danger")
        return redirect(url_for('dashboard'))
    
    form = WatchlistNoteForm()
    if form.validate_on_submit():
        try:
            item.notes = form.notes.data if form.notes.data else ""
            db.session.commit()
            flash("Notes updated successfully", "success")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating watchlist notes: {str(e)}")
            flash(f"Error updating notes: {str(e)}", "danger")
    else:
        flash("Form validation failed", "danger")
    
    return redirect(url_for('dashboard'))

@app.route('/stock/search')
@login_required
def search_stocks():
    """Search for stock symbols"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    try:
        results = get_stock_symbols(query)
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error searching for stocks: {str(e)}")
        return jsonify([])

@app.route('/stock/price/<symbol>')
@login_required
def get_stock_price_api(symbol):
    """Get the current price of a stock"""
    try:
        price = get_stock_price(symbol)
        if price is None:
            return jsonify({'error': 'Symbol not found'}), 404
        return jsonify({'symbol': symbol, 'price': price})
    except Exception as e:
        logger.error(f"Error getting stock price: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stock/daily-change/<symbol>')
@login_required
def get_stock_daily_change_api(symbol):
    """Get the daily change of a stock"""
    try:
        change, change_percent = get_daily_change(symbol)
        return jsonify({
            'symbol': symbol,
            'change': change,
            'change_percent': change_percent
        })
    except Exception as e:
        logger.error(f"Error getting daily change: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/reports')
@login_required
def reports():
    """View reports page"""
    form = ReportGeneratorForm()
    return render_template('reports.html', title='Reports', form=form)

@app.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    """Generate a portfolio report"""
    form = ReportGeneratorForm()
    if form.validate_on_submit():
        report_type = form.report_type.data
        
        try:
            # Get portfolio data
            portfolio_items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
            portfolio_data = []
            total_investment = 0
            total_current_value = 0
            top_gainer = None
            top_loser = None
            
            for item in portfolio_items:
                current_price = get_stock_price(item.symbol)
                if current_price is None:
                    continue
                    
                investment = item.quantity * item.buy_price
                current_value = item.quantity * current_price
                gain_loss = current_value - investment
                gain_loss_percent = (gain_loss / investment) * 100 if investment > 0 else 0
                
                total_investment += investment
                total_current_value += current_value
                
                item_data = {
                    'symbol': item.symbol,
                    'quantity': item.quantity,
                    'buy_price': item.buy_price,
                    'current_price': current_price,
                    'investment': investment,
                    'current_value': current_value,
                    'gain_loss': gain_loss,
                    'gain_loss_percent': gain_loss_percent
                }
                portfolio_data.append(item_data)
                
                # Track top gainer and loser
                if top_gainer is None or gain_loss_percent > top_gainer['gain_percent']:
                    top_gainer = {'symbol': item.symbol, 'gain_percent': gain_loss_percent}
                
                if top_loser is None or gain_loss_percent < top_loser['loss_percent']:
                    top_loser = {'symbol': item.symbol, 'loss_percent': gain_loss_percent}
            
            if not portfolio_data:
                flash("You don't have any items in your portfolio to generate a report", "warning")
                return redirect(url_for('reports'))
            
            # Prepare report data
            now = datetime.now()
            report_data = {
                'username': current_user.username,
                'month': now.strftime('%B'),
                'year': now.strftime('%Y'),
                'total_investment': total_investment,
                'total_current_value': total_current_value,
                'net_gain_loss': total_current_value - total_investment,
                'net_gain_loss_percent': ((total_current_value - total_investment) / total_investment) * 100 if total_investment > 0 else 0,
                'portfolio': portfolio_data,
                'top_gainer': top_gainer,
                'top_loser': top_loser
            }
            
            # Generate report based on selected type
            if report_type == 'pdf':
                output_path = generate_monthly_report_pdf(report_data)
                if output_path:
                    return send_file(
                        output_path,
                        as_attachment=True,
                        download_name=f"portfolio_report_{now.strftime('%Y%m%d')}.pdf"
                    )
            elif report_type == 'excel':
                output_path = generate_monthly_report_excel(report_data)
                if output_path:
                    return send_file(
                        output_path,
                        as_attachment=True,
                        download_name=f"portfolio_report_{now.strftime('%Y%m%d')}.xlsx"
                    )
            
            flash("Error generating report", "danger")
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            flash(f"Error generating report: {str(e)}", "danger")
    else:
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            logger.error(f"Error formatting form errors: {str(e)}")
            flash("Form validation failed", "danger")
    
    return redirect(url_for('reports'))

@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('404.html', title='Page Not Found'), 404

@app.errorhandler(500)
def internal_server_error(e):
    """Handle 500 errors"""
    logger.error(f"Internal Server Error: {str(e)}")
    return render_template('500.html', title='Server Error'), 500
