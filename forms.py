from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class PortfolioItemForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired(), Length(max=20)])
    quantity = FloatField('Quantity', validators=[DataRequired()])
    buy_price = FloatField('Buy Price', validators=[DataRequired()])
    exchange = SelectField('Exchange', choices=[('NSE', 'NSE'), ('BSE', 'BSE')], validators=[DataRequired()])
    submit = SubmitField('Add to Portfolio')

class WatchlistItemForm(FlaskForm):
    symbol = StringField('Stock Symbol', validators=[DataRequired(), Length(max=20)])
    exchange = SelectField('Exchange', choices=[('NSE', 'NSE'), ('BSE', 'BSE')], validators=[DataRequired()])
    notes = TextAreaField('Notes')
    submit = SubmitField('Add to Watchlist')

class WatchlistNoteForm(FlaskForm):
    notes = TextAreaField('Notes')
    submit = SubmitField('Update Notes')

class ReportGeneratorForm(FlaskForm):
    report_type = SelectField('Report Format', choices=[('pdf', 'PDF'), ('excel', 'Excel')], validators=[DataRequired()])
    submit = SubmitField('Generate Report')
