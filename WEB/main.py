from flask import Flask, render_template, request, redirect, abort

import base64
import ast
from time import time
import requests
import os

from WEB.models.students import Students
from models.users import User
from models.news import News
from models.friends import Friends
from models.messages import Messages
from models.images import Images
from models import db_session
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from forms.login import LoginForm
from forms.reg_form import RegForm
from forms.news_form import NewsForm
from forms.sms_form import SmsForm
from forms.edit_news_form import EditNewsForm
from forms.user_edit import UserEditForm
from translate import eng_to_rus, rus_to_eng, make_translate
from time_news import get_str_time
import datetime
from check_correct_data_input import check_correct_email, check_correct_password, check_correct_domen_user
import git

from api import get_setup
import pytz
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ebfqwejg;asdlp1LJNpjqwfffaffaWFEKffffwwwjwEKHFNLk;llffldmsdg'
db_session.global_init("db/db.db")


list = ['Международный', 'Всероссийский', 'Федеральный', 'Региональный', 'Городской', 'Районный', 'Школьный']


def main():
    db_session.global_init("db/db.db")
    app.run(debug=True)


serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
login_manager = LoginManager()
login_manager.init_app(app)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')


@app.errorhandler(401)
def page_not_found(e):
    return render_template('404.html')


database = []


@app.route('/send', methods=['POST'])
def send():
    data = request.json

    name = data['name']
    text = data['text']

    if not isinstance(data, dict) or 'name' not in data or 'text' not in data:
        return abort(404)

    message = {
        'name': name,
        'text': text,
        'time': time()
    }

    database.append(message)

    return {'ok': True}


@app.route('/all_users', methods=['GET', 'POST'])
def all_users():
    if not current_user.is_authenticated:
        return abort(404)

    db_sess = db_session.create_session()
    users = db_sess.query(User).filter(User.id != current_user.id).all()
    users = sorted(users, key=lambda x: (x.surname, x.name))
    all_image = []
    for elem in users:
        image = db_sess.query(Images).filter(Images.user_id == elem.id).first().b64_image
        encoded_string = str(image)
        encoded_string = encoded_string.replace("b'", '').replace("'", '')
        all_image.append(encoded_string)

    if request.method == 'POST' and 'search' in request.form and len(request.form['search'].strip()) > 0:
        users = list(filter(lambda x: request.form['search'].lower() in x.name.lower(), users))
        all_image = []
        for elem in users:
            print(elem.id)
            image = db_sess.query(Images).filter(Images.user_id == elem.id).first()
            print(image.user_id)
            encoded_string = str(image.b64_image)
            encoded_string = encoded_string.replace("b'", '').replace("'", '')
            all_image.append(encoded_string)
        return render_template('all_users.html', users=users, action='btn', image=all_image)
    return render_template('all_users.html', users=users, action='', image=all_image)



@app.route('/secret_update', methods=["POST"])
def webhook():
    if request.method == 'POST':
        repo = git.Repo('')
        origin = repo.remotes.origin
        origin.pull()
        return 'Ok', 200
    else:
        return 'No', 400


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.get(User, user_id)


@app.route('/c')
@login_required
def c():
    db_sess = db_session.create_session()
    students = db_sess.query(Students).filter(Students.author == current_user.id).all()
    return render_template('c.html', students=students, title='Участники')


@app.route('/uchreg', methods=['GET', 'POST'])
@login_required
def uchreg():
    db_sess = db_session.create_session()

    if request.method == 'POST':
        # Добавление нового участника
        name = request.form.get('name')
        place = request.form.get('place')

        if name and place:
            student = Students(name=name, place=place, author=current_user.id)
            db_sess.add(student)
            db_sess.commit()
            return redirect('/c')

    # Получение всех участников
    students = db_sess.query(Students).filter(Students.author == current_user.id).all()
    return render_template('uchreg.html', students=students, title='Регистрация участников')



@app.route('/', methods=['GET', 'POST'])
def first():
    db_sess = db_session.create_session()
    text = ''
    if request.method == 'POST':
        if 'confirm' in request.form:
            user = db_sess.query(User).filter(User.email == current_user.email).first()
            confirmation_code = serializer.dumps(user.id, salt='confirm-salt')
            confirm_url = f'{request.host}/confirm/{confirmation_code}'
            msg = MIMEText(f'''Подтвердите учетную запись от Gim17, перейдя по ссылке: {confirm_url}.\n 
                Если вы не отправляли запрос, игнорируйте это сообщение''', 'html')
            msg['Subject'] = 'Account Confirmation Required'
            msg['From'] = 'kvondeniz@yandex.ru'
            msg['To'] = user.email

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login('kvondeniz@yandex.ru', 'hafg vjqg nywe khnu')
                server.sendmail('valerylarionov06@gmail.com', [user.email], msg.as_string())
                text = 'Зайдите на почту и подтвердите свою учетную запись в течение трёх минут'

    news = db_sess.query(News).all()
    news = news[::-1]

    authors = []
    confirmed_check = []
    for new in news:
        name = db_sess.query(User).filter(User.id == new.author).first().name
        surname = db_sess.query(User).filter(User.id == new.author).first().surname
        confirm = db_sess.query(User).filter(User.id == new.author).first().confirmed
        confirmed_check.append(confirm)
        authors.append(f"{name} {surname}")
        # new.data = get_str_time(new.data)


    info = {
        'news': news,
        'authors': authors,
        'confirm_check': confirmed_check
    }
    if current_user.is_authenticated:
        image = db_sess.query(Images).filter(Images.user_id == current_user.id).first()
        if not image:
            with open(f'static/img/user.jpg', 'rb') as file:
                encoding_image = base64.b64encode(file.read())
            image = Images(user_id=current_user.id,
                           b64_image=encoding_image)
            db_sess.add(image)
            db_sess.commit()
    result_image = []
    for elem in news:
        image = db_sess.query(Images).filter(Images.user_id == elem.author).first().b64_image
        encoded_string = str(image)
        encoded_string = encoded_string.replace("b'", '').replace("'", '')
        result_image.append(encoded_string)



    return render_template('news.html', **info, title='Gim17', text=text, action='', image=result_image)



@app.route('/edit_news/<int:id>', methods=['GET', 'POST'])
@login_required
def news_edit(id):
    if not current_user.is_authenticated:
        return abort(404)

    db_sess = db_session.create_session()
    form = EditNewsForm()
    if request.method == "GET":
        new_check = db_sess.query(News).filter(News.id == id).filter(News.author == current_user.id).first()
        if current_user.email == 'regeneration76@yandex.ru' or current_user.email == 'valerylarionov06@gmail.com':
            new_check = db_sess.query(News).filter(News.id == id).first()

        if new_check:
            form.name.data = new_check.name
            form.text.data = new_check.text
            form.level.data = new_check.level
            form.organizer.data = new_check.organizer
            form.format.data = new_check.format
            form.url.data = new_check.url
            form.place.data = new_check.place
            form.date.data = new_check.date

            form.private.data = new_check.private
        else:
            abort(404)
    if form.validate_on_submit():
        new_obj = db_sess.query(News).filter(News.id == id).filter(News.author == current_user.id).first()
        if current_user.email == 'regeneration76@yandex.ru' or current_user.email == 'valerylarionov06@gmail.com':
            new_obj = db_sess.query(News).filter(News.id == id).first()
        if 'edit' in request.form:
            if new_obj:
                if len(form.name.data.strip()) > 100:
                    return render_template('edit_news.html', title='Редактирование работы',
                                           form=form, action='',
                                           message=f'Слишком длинное название: {len(form.name.data.strip())} '
                                                   f'(максимум 100 символов)')

                if len(form.text.data.strip()) > 1000:
                    return render_template('edit_news.html', title='Редактирование работы',
                                           form=form, action='',
                                           message=f'Слишком длинное описание {len(form.text.data.strip())} '
                                                   f'(максимум 1000 символов)')

                if len(form.level.data.strip()) > 1000:
                    return render_template('edit_news.html', title='Редактирование работы',
                                           form=form, action='',
                                           message=f'Слишком длинное описание {len(form.level.data.strip())} '
                                                   f'(максимум 1000 символов)')
                new_obj.name = form.name.data.strip()
                new_obj.text = form.text.data
                new_obj.level = form.level.data
                new_obj.organizer = form.organizer.data
                new_obj.format = form.format.data
                new_obj.url = form.url.data
                new_obj.place = form.place.data
                new_obj.date = form.date.data
                # new_obj.date_field = form.date_field.data
                new_obj.private = form.private.data
                db_sess.commit()
                return redirect('/')

        elif 'confirm_del' in request.form:
            return render_template('edit_news.html', title='Редактирование работы', form=form,
                                   action='confirm_del')

        elif 'yes' in request.form:
            if new_obj:
                db_sess.delete(new_obj)
                db_sess.commit()
            else:
                abort(404)
            return redirect('/')
    return render_template('edit_news.html', form=form, title='Редактирование работы', action='')


@app.route('/edit_home/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_home(id):
    if not current_user.is_authenticated:
        return abort(404)

    db_sess = db_session.create_session()
    if id != current_user.id:
        abort(404)

    form = UserEditForm()
    if request.method == "GET":
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == current_user.id).first()
        form.name.data = user.name
        form.surname.data = user.surname
        form.city.data = user.city
        form.age.data = user.age
        form.setup_see.data = user.setup_see
        form.domen.data = user.domen

    if request.method == 'POST' and 'ava' in request.form:
        return redirect('/ava')

    if form.validate_on_submit():
        age = form.age.data
        if age < 1 or age > 150:
            return render_template('user_edit.html', message="Что с возрастом?", form=form,
                                   title='Редактирование профиля')
        name = form.name.data.strip()
        if len(name) > 30:
            return render_template('user_edit.html', message="Ошибка: Слишком длинное имя", form=form,
                                   title='Редактирование профиля')
        surname = form.surname.data.strip()
        if len(surname) > 30:
            return render_template('user_edit.html', message="Ошибка: Слишком длинная фамилия",
                                   form=form,
                                   title='Редактирование профиля')
        city = form.city.data.strip()
        if len(city) > 50:
            return render_template('user_edit.html', message="Ошибка: Слишком длинный город",
                                   form=form,
                                   title='Редактирование профиля')
        if not city.strip():
            city = 'Не указан'

        domen = form.domen.data
        if domen is not None:
            check_domen = check_correct_domen_user(domen)
            if not check_domen[0]:
                return render_template('user_edit.html', message=f"Ошибка: {check_domen[1]}",
                                       form=form,
                                       title='Редактирование профиля')

        setup_see = form.setup_see.data
        user = db_sess.query(User).filter(User.id == current_user.id).first()

        if (domen is not None) and (str(domen) != str(user.domen)):
            if domen.isdigit():
                return render_template('user_edit.html',
                                       message=f'Ошибка: В изменённом псевдониме должен быть хотя '
                                               f'бы один латинский символ или "_"',
                                       form=form,
                                       title='Редактирование профиля')

        all_users = db_sess.query(User).filter(User.id != current_user.id).all()
        for elem in all_users:
            if elem.domen == domen:
                return render_template('user_edit.html', message=f"Ошибка: Данный псевдоним занят",
                                       form=form,
                                       title='Редактирование профиля')

        if form.update_setup.data:
            user.setup = get_setup()

        user.name = name
        user.surname = surname
        user.age = age
        user.city = city
        user.setup_see = setup_see
        if domen is not None:
            user.domen = domen
        db_sess.commit()

        return redirect(f'/home/{current_user.id}')

    return render_template('user_edit.html', title='Редактирование профиля', form=form, action='')


@app.route("/ava", methods=['GET', 'POST'])
def her():
    if request.method == 'POST':
        # Получаем имя файла
        f = request.files['file']

        # Проверяем, был ли выбран файл
        if f.filename == '':
            return render_template('her.html', message='нет файла')

        # Создаем уникальное имя файла
        new_file = f'{current_user.id}.png'
        f = request.files['file']

        check = f.filename
        check = check.split('.')
        if check[-1] not in ['png', 'jpg']:
            return render_template('her.html', message='поддерживаются только файлы с '
                                                       'расширением png и jpg')

        with open(f'static/img/ava/{new_file}', 'wb') as file:
            file.write(f.read())

        with open(f'static/img/ava/{new_file}', 'rb') as file:
            encoding_image = base64.b64encode(file.read())

        db_sess = db_session.create_session()
        image = db_sess.query(Images).filter(Images.user_id == current_user.id).first()
        if not image:
            with open(f'static/img/ava/{new_file}', 'rb') as file:
                encoding_image = base64.b64encode(file.read())
            image = Images(user_id=current_user.id,
                           b64_image=encoding_image)
            db_sess.add(image)
        else:
            image.b64_image = encoding_image
            db_sess.add(image)
        db_sess.commit()
        os.remove(f'static/img/ava/{new_file}')

        return redirect(f'home/{current_user.id}')

    return render_template('her.html')


@app.route('/confirm/<confirmation_code>')
def confirm(confirmation_code):
    if not current_user.is_authenticated:
        return abort(404)

    db_sess = db_session.create_session()
    try:
        unconfirmed_user_id = serializer.loads(confirmation_code, salt='confirm-salt', max_age=180)
        user = db_sess.query(User).filter(User.id == unconfirmed_user_id).first()

        ava = db_sess.query(Images).filter(Images.user_id == current_user.id).first()
        if not ava:
            with open('static/img/user.jpg', 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read())
            image = Images(user_id=current_user.id,
                           b64_image=encoded_string)
            db_sess.add(image)
            db_sess.commit()
        else:
            encoded_string = ava.b64_image
        encoded_string = str(encoded_string)
        encoded_string = encoded_string.replace("b'", '').replace("'", '')

        if unconfirmed_user_id is not None:
            user.confirmed = True
            db_sess.commit()

            return render_template('home.html', text='Вы подтвердили вашу учетную запись',
                                   stop='stop', ava=encoded_string)
        else:
            return render_template('confirmed_sms.html', title='NaSvyazi', text='Неизвестная ошибка')
    except Exception as text:
        return render_template('confirmed_sms.html', title='NaSvyazi',
                               text='Ошибка, возможно, превышено время. Попробуйте еще раз')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if current_user.is_authenticated:
        abort(404)

    form = RegForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        check_user = db_sess.query(User)
        if check_user.filter(User.email == form.email.data).first():
            return render_template('registration.html',
                                   message="Ошибка регистрации: пользователь с такой почтой уже существует", form=form,
                                   title='Регистрация')
        age = form.age.data
        if age < 1 or age > 150:
            return render_template('registration.html', message="Ошибка регистрации: что с возрастом?",
                                   form=form, title='Регистрация')

        name = form.name.data.strip()
        if len(name) > 30:
            return render_template('registration.html',
                                   message="Ошибка регистрации: Слишком длинное имя", form=form,
                                   title='Регистрация')

        surname = form.surname.data.strip()
        if len(surname) > 30:
            return render_template('registration.html',
                                   message="Ошибка регистрации: Слишком длинная фамилия", form=form,
                                   title='Регистрация')

        if not form.city.data:
            city = 'Не указан'
        else:
            city = form.city.data.strip()

        if len(city) > 50:
            return render_template('registration.html',
                                   message="Ошибка регистрации: Слишком длинный город", form=form,
                                   title='Регистрация')

        if not check_correct_email(form.email.data)[0]:
            return render_template('registration.html', message="Ошибка регистрации: плохая почта",
                                   form=form,
                                   title='Регистрация')

        check_password = check_correct_password(form.password.data)
        if not check_password[0]:
            return render_template('registration.html', message=f"Ошибка регистрации: "
                                                                f"{check_password[1]}", form=form, title='Регистрация')
        if form.password.data != form.repeat_password.data:
            return render_template('registration.html', message=f"Ошибка регистрации: "
                                                                f"пароли не совпадают", form=form, title='Регистрация')

        setup = get_setup()
        user = User(
            name=name,
            surname=surname,
            email=form.email.data,
            age=form.age.data,
            city=city,
            setup=setup,
            domen='ы'
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()

        user_info = db_sess.query(User).filter(User.email == form.email.data).first()
        user_info.domen = str(user_info.id)
        db_sess.commit()

        login_user(user_info, remember=form.remember_me.data)
        return redirect('/')
    return render_template('registration.html', form=form, title='Регистрация')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if not user:
            return render_template('login.html',
                                   message="Неправильный логин",
                                   form=form, title='Вход')
        elif not user.check_password(form.password.data):
            user.set_password(form.password.data)
            return render_template('login.html',
                                   message="Неправильный пароль",
                                   form=form, title='Вход')
        login_user(user, remember=form.remember_me.data)
        return redirect("/")

    return render_template('login.html', title='Авторизация', form=form)


@login_required
@app.route('/new_news', methods=['GET', 'POST'])
def new_news():
    if not current_user.is_authenticated:
        abort(404)
    form = NewsForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user_id = db_sess.query(User).filter(User.email == current_user.email).first().id
        if len(form.name.data.strip()) > 100:
            return render_template('new_news.html',
                                   title='Редактирование работы',
                                   form=form,
                                   message='Слишком длинное название (максимум 100 символов)')
        if len(form.text.data.strip()) > 1000:
            return render_template('new_news.html',
                                   title='Редактирование работы',
                                   form=form,
                                   message='Слишком длинное описание (максимум 1000 символов)')

        if form.date.data and form.date.data < datetime.date.today():
            return render_template('new_news.html',
                                   title='Новый конкурс',
                                   form=form,
                                   message='Дата не может быть в прошлом')

        news = News(
            author=user_id,
            name=form.name.data,
            text=form.text.data,
            level=form.level.data,
            format=form.format.data,
            organizer=form.organizer.data,
            url=form.url.data,
            place=form.place.data,
            date=form.date.data,  # Добавлено поле даты
            private=form.private.data,
        )
        db_sess.add(news)
        db_sess.commit()
        tz_kiev = pytz.timezone('Europe/Kiev')
        time_kiev = datetime.datetime.now(tz_kiev)
        news.data = time_kiev
        news.data_str = get_str_time(news.data)
        db_sess.commit()
        return redirect("/")
    return render_template('new_news.html', form=form, title='Новый конкурс')


def send_email(db_sess):
    user = db_sess.query(User).filter(User.email == current_user.email).first()
    confirmation_code = serializer.dumps(user.id, salt='confirm-salt')
    confirm_url = f'{request.host}/confirm/{confirmation_code}'
    msg = MIMEText(f'''Please confirm your account by clicking the link below: {confirm_url}''', 'html')
    msg['Subject'] = 'Account Confirmation Required'
    msg['From'] = 'kvondeniz@yandex.ru'
    msg['To'] = user.email

    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('kvondeniz@yandex.ru', 'hafg vjqg nywe khnu')
        server.sendmail('kvondeniz@yandex.ru', [user.email], msg.as_string())


@app.route('/home/<int:id>', methods=['GET', 'POST'])
def home(id):
    if not current_user.is_authenticated:
        return abort(404)

    try:
        id_user = current_user.id
    except Exception:
        abort(404)
    if id_user == id:
        db_sess = db_session.create_session()
        news = db_sess.query(News).filter(News.author == current_user.id).all()

        ava = db_sess.query(Images).filter(Images.user_id == current_user.id).first()
        if not ava:
            with open('static/img/user.jpg', 'rb') as image_file:
                encoded_string = base64.b64encode(image_file.read())
            image = Images(user_id=current_user.id,
                           b64_image=encoded_string)
            db_sess.add(image)
            db_sess.commit()
        else:
            encoded_string = ava.b64_image
        encoded_string = str(encoded_string)
        encoded_string = encoded_string.replace("b'", '').replace("'", '')

        news = news[::-1]
        if 'confirm' in request.form:
            send_email(db_sess)
            return render_template('home.html', title=current_user.name,
                                   text='Зайдите на почту и подтвердите свою учетную запись в течение трёх минут',
                                   news=news, ava=encoded_string)
        return render_template('home.html', title=current_user.name, text='', news=news,
                               ava=encoded_string)
    else:
        abort(404)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/im', methods=['GET', 'POST'])
def im():
    if not current_user.is_authenticated:
        return '<h1 align="center">Войдите в аккаунт ;)</h1>'
    form = SmsForm()
    id_user = request.args.get('sel')
    id_chat = request.args.get('ch')

    db_sess = db_session.create_session()
    is_friends = db_sess.query(Friends).filter(Friends.first_id == current_user.id,
                                               Friends.second_id == id_user).all()
    if is_friends:
        user = db_sess.query(User).filter(User.id == id_user).first()
    else:
        return redirect('404')

    if user:
        return render_template(template_name_or_list='im.html', form=form, title=user.name)





@app.route('/help')
def help_handler():
    return render_template('help.html')


if __name__ == '__main__':
    main()
