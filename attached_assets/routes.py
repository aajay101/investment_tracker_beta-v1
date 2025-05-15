import os
from flask import render_template, url_for, flash, redirect, request, jsonify, send_file, g
from flask_login import login_user, current_user, logout_user, login_required
from urllib.parse import urlparse
from app import app, db
from models import User, PortfolioItem, WatchlistItem, PortfolioHistory
from forms import RegistrationForm, LoginForm, PortfolioItemForm, WatchlistItemForm, WatchlistNoteForm, ReportGeneratorForm
from stock_utils import get_stock_price, get_stock_history, get_stock_symbols, get_daily_change
from report_generator import generate_monthly_report_pdf, generate_monthly_report_excel
from form_helpers import format_form_errors, get_field_label
import datetime
import logging
import tempfile

@app.context_processor
def inject_now():
    # Add current date to all templates
    return {'now': datetime.datetime.now()}

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html', title='Investment Dashboard')

@app.route('/register', methods=['GET', 'POST'])
def register():
    print("Register route accessed")
    if current_user.is_authenticated:
        print("User already authenticated, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    
    form = RegistrationForm()
    print(f"Request method: {request.method}")
    if form.validate_on_submit():
        print(f"Form validated, username: {form.username.data}, email: {form.email.data}")
        try:
            # Create new user - ensure values aren't None
            username = form.username.data if form.username.data else ""
            email = form.email.data if form.email.data else ""
            password = form.password.data if form.password.data else ""
            
            # Input validation
            if not username or not email or not password:
                print("Missing required fields")
                flash('All fields are required', 'danger')
                return render_template('register.html', title='Register', form=form)
            
            user = User()
            user.username = username
            user.email = email
            user.set_password(password)
            
            # Add to database
            print("Adding user to database...")
            db.session.add(user)
            db.session.commit()
            print(f"User created successfully with id: {user.id}")
            
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error creating user: {str(e)}")
            flash(f'An error occurred during registration: {str(e)}', 'danger')
    elif request.method == 'POST':
        print(f"Form validation failed. Errors: {form.errors}")
        # Use our helper function to format and display errors
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            print(f"Error formatting flash messages: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Login route accessed")
    if current_user.is_authenticated:
        print("User already authenticated, redirecting to dashboard")
        return redirect(url_for('dashboard'))
    
    form = LoginForm()
    print(f"Request method: {request.method}")
    if form.validate_on_submit():
        print(f"Form validated, username: {form.username.data}")
        
        # Handle possible None values
        username = form.username.data if form.username.data else ""
        password = form.password.data if form.password.data else ""
        
        # Check for empty inputs
        if not username or not password:
            print("Missing username or password")
            flash('Both username and password are required', 'danger')
            return render_template('login.html', title='Login', form=form)
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"User found: {user.username}, id: {user.id}")
            password_check = user.check_password(password)
            print(f"Password check result: {password_check}")
            
            if password_check:
                print("Login successful, calling login_user()")
                login_user(user)
                next_page = request.args.get('next')
                print(f"Next page: {next_page}")
                
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('dashboard')
                
                print(f"Redirecting to: {next_page}")
                flash('Login successful!', 'success')
                return redirect(next_page)
        
        print("Login failed - invalid username or password")
        flash('Login unsuccessful. Please check username and password.', 'danger')
    elif request.method == 'POST':
        print(f"Form validation failed. Errors: {form.errors}")
        # Use our helper function to format and display errors
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            print(f"Error formatting flash messages: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
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
            logging.error(f"Error fetching data for {item.symbol}: {str(e)}")
            flash(f"Unable to fetch current price for {item.symbol}", "warning")
    
    total_gain_loss = total_current_value - total_investment
    total_gain_loss_percent = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
    
    # Save portfolio history for today if not already saved
    today = datetime.date.today()
    existing_history = PortfolioHistory.query.filter_by(
        user_id=current_user.id, 
        date=today
    ).first()
    
    if not existing_history and total_current_value > 0:
        # Get yesterday's record if available to calculate daily change
        yesterday = today - datetime.timedelta(days=1)
        yesterday_history = PortfolioHistory.query.filter_by(
            user_id=current_user.id,
            date=yesterday
        ).first()
        
        daily_change = 0
        daily_change_percent = 0
        
        if yesterday_history:
            daily_change = total_current_value - yesterday_history.total_value
            daily_change_percent = (daily_change / yesterday_history.total_value) * 100 if yesterday_history.total_value > 0 else 0
        
        portfolio_history = PortfolioHistory()
        portfolio_history.user_id = current_user.id
        portfolio_history.date = today
        portfolio_history.total_value = total_current_value
        portfolio_history.daily_change = daily_change
        portfolio_history.daily_change_percent = daily_change_percent
        db.session.add(portfolio_history)
        db.session.commit()
    
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
    
    # Ensure all values in performance_data are JSON serializable
    for key in performance_data:
        if isinstance(performance_data[key], list):
            # Convert any non-serializable elements in lists
            performance_data[key] = [float(x) if isinstance(x, (int, float)) and not isinstance(x, bool)
                                    else str(x) if not isinstance(x, (str, bool, type(None)))
                                    else x
                                    for x in performance_data[key]]
    
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
        performance_data=performance_data
    )

@app.route('/portfolio/add', methods=['POST'])
@login_required
def add_portfolio_item():
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
            print(f"Validating stock symbol: {symbol}")
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
            print(f"Creating portfolio item: {symbol}, {quantity}, {buy_price}, {exchange}")
            portfolio_item = PortfolioItem()
            portfolio_item.symbol = symbol.upper()
            portfolio_item.quantity = quantity
            portfolio_item.buy_price = buy_price
            portfolio_item.exchange = exchange
            portfolio_item.user_id = current_user.id
            
            db.session.add(portfolio_item)
            db.session.commit()
            print(f"Portfolio item created successfully with id: {portfolio_item.id}")
            
            flash(f"{symbol.upper()} added to your portfolio successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding portfolio item: {str(e)}")
            print(f"Error adding portfolio item: {str(e)}")
            flash(f"Failed to add stock: {str(e)}", "danger")
            return redirect(url_for('dashboard'))
    else:
        print(f"Form validation failed. Errors: {form.errors}")
        # Use our helper function to format and display errors
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            print(f"Error formatting flash messages: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return redirect(url_for('dashboard'))

@app.route('/portfolio/edit/<int:item_id>', methods=['POST'])
@login_required
def edit_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    
    # Ensure the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to edit this item.", "danger")
        return redirect(url_for('dashboard'))
    
    quantity = request.form.get('quantity', type=float)
    buy_price = request.form.get('buy_price', type=float)
    exchange = request.form.get('exchange')
    
    if quantity is None or buy_price is None or not exchange:
        flash("Invalid data provided. Please check your inputs.", "danger")
        return redirect(url_for('dashboard'))
    
    item.quantity = quantity
    item.buy_price = buy_price
    item.exchange = exchange
    db.session.commit()
    
    flash(f"{item.symbol} updated successfully!", "success")
    return redirect(url_for('dashboard'))

@app.route('/portfolio/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_portfolio_item(item_id):
    item = PortfolioItem.query.get_or_404(item_id)
    
    # Ensure the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to delete this item.", "danger")
        return redirect(url_for('dashboard'))
    
    symbol = item.symbol
    db.session.delete(item)
    db.session.commit()
    
    flash(f"{symbol} removed from your portfolio.", "success")
    return redirect(url_for('dashboard'))

@app.route('/stock/history/<symbol>')
@login_required
def stock_history(symbol):
    period = request.args.get('period', '1mo')  # Default to 1 month
    valid_periods = {'1d': '1 Day', '1wk': '1 Week', '1mo': '1 Month', '1y': '1 Year'}
    
    if period not in valid_periods:
        period = '1mo'
    
    try:
        history = get_stock_history(symbol, period)
        
        # Ensure history data is JSON serializable
        for item in history:
            for key, value in item.items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    item[key] = float(value)
                elif not isinstance(value, (str, bool, type(None))):
                    item[key] = str(value)
        
        title = f'{symbol} - {valid_periods[period]} History'
        
        return render_template(
            'stock_history.html',
            title=title,
            symbol=symbol,
            period=period,
            valid_periods=valid_periods,
            history=history
        )
    except Exception as e:
        logging.error(f"Error getting stock history for {symbol}: {str(e)}")
        flash(f"Unable to fetch history data for {symbol}. Please try again later.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/watchlist')
@login_required
def watchlist():
    form = WatchlistItemForm()
    note_form = WatchlistNoteForm()
    
    watchlist_items = WatchlistItem.query.filter_by(user_id=current_user.id).all()
    watchlist_data = []
    
    for item in watchlist_items:
        try:
            current_price = get_stock_price(item.symbol)
            daily_change, daily_change_percent = get_daily_change(item.symbol)
            
            watchlist_data.append({
                'id': item.id,
                'symbol': item.symbol,
                'exchange': item.exchange,
                'current_price': current_price,
                'daily_change': daily_change,
                'daily_change_percent': daily_change_percent,
                'notes': item.notes
            })
        except Exception as e:
            logging.error(f"Error fetching data for watchlist item {item.symbol}: {str(e)}")
            flash(f"Unable to fetch current price for {item.symbol}", "warning")
            
            watchlist_data.append({
                'id': item.id,
                'symbol': item.symbol,
                'exchange': item.exchange,
                'current_price': 'N/A',
                'daily_change': 'N/A',
                'daily_change_percent': 'N/A',
                'notes': item.notes
            })
    
    return render_template(
        'watchlist.html',
        title='Watchlist',
        form=form,
        note_form=note_form,
        watchlist_data=watchlist_data
    )

@app.route('/watchlist/add', methods=['POST'])
@login_required
def add_watchlist_item():
    form = WatchlistItemForm()
    if form.validate_on_submit():
        # Get form data with null checks
        symbol = form.symbol.data if form.symbol.data else ""
        
        # Validate required fields
        if not symbol:
            flash("Stock symbol is required", "danger")
            return redirect(url_for('watchlist'))
            
        try:
            # Check if stock symbol is valid
            print(f"Validating watchlist stock symbol: {symbol}")
            current_price = get_stock_price(symbol)
            if current_price is None:
                flash(f"Invalid stock symbol: {symbol}. Please check and try again.", "danger")
                return redirect(url_for('watchlist'))
                
            # Get remaining form data
            exchange = form.exchange.data if form.exchange.data else "NSE"
            notes = form.notes.data if form.notes.data else ""
            
            # Add the watchlist item
            print(f"Creating watchlist item: {symbol}, {exchange}")
            watchlist_item = WatchlistItem()
            watchlist_item.symbol = symbol.upper()
            watchlist_item.exchange = exchange
            watchlist_item.notes = notes
            watchlist_item.user_id = current_user.id
            
            db.session.add(watchlist_item)
            db.session.commit()
            print(f"Watchlist item created successfully with id: {watchlist_item.id}")
            
            flash(f"{symbol.upper()} added to your watchlist successfully!", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error adding watchlist item: {str(e)}")
            print(f"Error adding watchlist item: {str(e)}")
            flash(f"Failed to add to watchlist: {str(e)}", "danger")
            return redirect(url_for('watchlist'))
    else:
        print(f"Form validation failed. Errors: {form.errors}")
        # Use our helper function to format and display errors
        try:
            format_form_errors(form, form.errors)
        except Exception as e:
            print(f"Error formatting flash messages: {str(e)}")
            flash("Form validation failed. Please check your inputs.", "danger")
    
    return redirect(url_for('watchlist'))

@app.route('/watchlist/notes/<int:item_id>', methods=['POST'])
@login_required
def update_watchlist_notes(item_id):
    item = WatchlistItem.query.get_or_404(item_id)
    
    # Ensure the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to edit this item.", "danger")
        return redirect(url_for('watchlist'))
    
    form = WatchlistNoteForm()
    if form.validate_on_submit():
        item.notes = form.notes.data
        db.session.commit()
        flash("Notes updated successfully.", "success")
    
    return redirect(url_for('watchlist'))

@app.route('/watchlist/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_watchlist_item(item_id):
    item = WatchlistItem.query.get_or_404(item_id)
    
    # Ensure the item belongs to the current user
    if item.user_id != current_user.id:
        flash("You don't have permission to delete this item.", "danger")
        return redirect(url_for('watchlist'))
    
    symbol = item.symbol
    db.session.delete(item)
    db.session.commit()
    
    flash(f"{symbol} removed from your watchlist.", "success")
    return redirect(url_for('watchlist'))

@app.route('/reports')
@login_required
def reports():
    form = ReportGeneratorForm()
    
    # Get some basic stats for the reports page
    portfolio_items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
    total_investment = 0
    total_current_value = 0
    top_gainer = {"symbol": "N/A", "gain_percent": 0}
    top_loser = {"symbol": "N/A", "loss_percent": 0}
    
    for item in portfolio_items:
        try:
            current_price = get_stock_price(item.symbol)
            investment = item.quantity * item.buy_price
            current_value = item.quantity * current_price
            gain_loss = current_value - investment
            gain_loss_percent = (gain_loss / investment) * 100 if investment > 0 else 0
            
            total_investment += investment
            total_current_value += current_value
            
            # Check for top gainer/loser
            if gain_loss_percent > top_gainer["gain_percent"]:
                top_gainer = {"symbol": item.symbol, "gain_percent": gain_loss_percent}
            
            if gain_loss_percent < top_loser["loss_percent"]:
                top_loser = {"symbol": item.symbol, "loss_percent": gain_loss_percent}
                
        except Exception as e:
            logging.error(f"Error calculating portfolio stats for {item.symbol}: {str(e)}")
    
    net_gain_loss = total_current_value - total_investment
    net_gain_loss_percent = (net_gain_loss / total_investment) * 100 if total_investment > 0 else 0
    
    # Get performance history for month
    today = datetime.date.today()
    first_of_month = today.replace(day=1)
    history_data = PortfolioHistory.query.filter(
        PortfolioHistory.user_id == current_user.id,
        PortfolioHistory.date >= first_of_month
    ).order_by(PortfolioHistory.date).all()
    
    # Create properly serializable data for the chart
    dates = []
    values = []
    daily_changes = []
    
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
    
    monthly_performance = {
        'dates': dates,
        'values': values,
        'daily_changes': daily_changes
    }
    
    # Ensure all values in monthly_performance are JSON serializable
    for key in monthly_performance:
        if isinstance(monthly_performance[key], list):
            # Convert any non-serializable elements in lists
            monthly_performance[key] = [float(x) if isinstance(x, (int, float)) and not isinstance(x, bool)
                                      else str(x) if not isinstance(x, (str, bool, type(None)))
                                      else x
                                      for x in monthly_performance[key]]
    
    return render_template(
        'reports.html',
        title='Reports',
        form=form,
        total_investment=total_investment,
        total_current_value=total_current_value,
        net_gain_loss=net_gain_loss,
        net_gain_loss_percent=net_gain_loss_percent,
        top_gainer=top_gainer,
        top_loser=top_loser,
        monthly_performance=monthly_performance
    )

@app.route('/reports/generate', methods=['POST'])
@login_required
def generate_report():
    form = ReportGeneratorForm()
    if form.validate_on_submit():
        report_type = form.report_type.data
        
        # Get portfolio data
        portfolio_items = PortfolioItem.query.filter_by(user_id=current_user.id).all()
        portfolio_data = []
        total_investment = 0
        total_current_value = 0
        top_gainer = {"symbol": "N/A", "gain_percent": 0}
        top_loser = {"symbol": "N/A", "loss_percent": 0}
        
        for item in portfolio_items:
            try:
                current_price = get_stock_price(item.symbol)
                investment = item.quantity * item.buy_price
                current_value = item.quantity * current_price
                gain_loss = current_value - investment
                gain_loss_percent = (gain_loss / investment) * 100 if investment > 0 else 0
                
                total_investment += investment
                total_current_value += current_value
                
                portfolio_data.append({
                    'symbol': item.symbol,
                    'quantity': item.quantity,
                    'buy_price': item.buy_price,
                    'current_price': current_price,
                    'investment': investment,
                    'current_value': current_value,
                    'gain_loss': gain_loss,
                    'gain_loss_percent': gain_loss_percent
                })
                
                # Check for top gainer/loser
                if gain_loss_percent > top_gainer["gain_percent"]:
                    top_gainer = {"symbol": item.symbol, "gain_percent": gain_loss_percent}
                
                if gain_loss_percent < top_loser["loss_percent"]:
                    top_loser = {"symbol": item.symbol, "loss_percent": gain_loss_percent}
                    
            except Exception as e:
                logging.error(f"Error calculating portfolio stats for {item.symbol}: {str(e)}")
        
        # Generate the report in the requested format
        today = datetime.date.today()
        month_name = today.strftime('%B')
        year = today.year
        net_gain_loss = total_current_value - total_investment
        
        report_data = {
            'username': current_user.username,
            'month': month_name,
            'year': year,
            'portfolio': portfolio_data,
            'total_investment': total_investment,
            'total_current_value': total_current_value,
            'net_gain_loss': net_gain_loss,
            'net_gain_loss_percent': (net_gain_loss / total_investment) * 100 if total_investment > 0 else 0,
            'top_gainer': top_gainer,
            'top_loser': top_loser
        }
        
        # Create a temporary file to store the report
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_filename = temp_file.name
        
        if report_type == 'pdf':
            generate_monthly_report_pdf(report_data, temp_filename)
            mimetype = 'application/pdf'
            output_filename = f'Investment_Report_{month_name}_{year}.pdf'
        else:  # Excel
            generate_monthly_report_excel(report_data, temp_filename)
            mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            output_filename = f'Investment_Report_{month_name}_{year}.xlsx'
        
        return send_file(
            temp_filename,
            mimetype=mimetype,
            as_attachment=True,
            download_name=output_filename
        )
    
    flash("Please select a valid report format.", "warning")
    return redirect(url_for('reports'))

@app.route('/api/search/stocks')
@login_required
def search_stocks():
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    try:
        results = get_stock_symbols(query)
        return jsonify(results)
    except Exception as e:
        logging.error(f"Error searching for stock symbols: {str(e)}")
        return jsonify([])

@app.route('/api/stock/price/<symbol>')
@login_required
def get_current_price(symbol):
    try:
        price = get_stock_price(symbol)
        daily_change, daily_change_percent = get_daily_change(symbol)
        return jsonify({
            'symbol': symbol,
            'price': price,
            'daily_change': daily_change,
            'daily_change_percent': daily_change_percent
        })
    except Exception as e:
        logging.error(f"Error getting stock price for {symbol}: {str(e)}")
        return jsonify({'error': 'Failed to fetch stock price'}), 500
