from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, EmailField, BooleanField, DateField
from wtforms.fields.numeric import IntegerField
from wtforms.validators import DataRequired


class RegUch(FlaskForm):
    name = StringField('*Имя', validators=[DataRequired()])
    submit = SubmitField('Создать аккаунт')
