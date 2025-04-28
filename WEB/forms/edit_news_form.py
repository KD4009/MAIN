from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField, EmailField, BooleanField, SelectField
from wtforms.validators import DataRequired


list = ['Международный', 'Всероссийский', 'Федеральный', 'Региональный', 'Городской', 'Районный', 'Школьный']


class EditNewsForm(FlaskForm):

    name = StringField('*Название конкурса', validators=[DataRequired()])
    text = StringField('*Номинация', validators=[DataRequired()])
    level = SelectField('*Уровень конкурса',
                        choices=[
                            ('', 'Выберите уровень'),
                            ('Международный', 'Международный'),
                            ('Всероссийский', 'Всероссийский'),
                            ('Федеральный', 'Федеральный'),
                            ('Региональный', 'Региональный'),
                            ('Городской', 'Городской'),
                            ('Районный', 'Районный'),
                            ('Университетский', 'Университетский'),
                            ('Школьный', 'Школьный')
                        ],
                        validators=[DataRequired()])
    organizer = StringField('*Организатор', validators=[DataRequired()])
    format = SelectField('*Формат',
                        choices=[
                            ('', 'Выберите формат'),
                            ('Очно', 'Очно'),
                            ('Дистанционно', 'Дистанционно'),
                        ],
                        validators=[DataRequired()])
    url = StringField('*Ссылка на итоги конкурса', validators=[DataRequired()])
    place = StringField('*Место проведения конкурса', validators=[DataRequired()])
    private = BooleanField('Сделать новость приватной')

