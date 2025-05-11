from flask import Flask, render_template, request, redirect, abort
import pandas as pd
from io import BytesIO
from flask import send_file
import base64
from time import time
import os
from models.students import Students
from models.users import User
from models.news import News
from models.images import Images
from models import db_session
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from forms.login import LoginForm
from forms.reg_form import RegForm
from forms.news_form import NewsForm
from forms.edit_news_form import EditNewsForm
from forms.user_edit import UserEditForm
from time_news import get_str_time
import datetime
from check_correct_data_input import check_correct_email, check_correct_password, check_correct_domen_user
import pytz
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText


app = Flask(__name__)
app.config['SECRET_KEY'] = '37f36414-d7e6-4f6a-8c4f-7e490e7ec745'
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


@app.route('/export_news_to_excel')
@login_required
def export_news_to_excel():
    if current_user.email not in ['kvondeniz@yandex.ru']:
        abort(403)

    db_sess = db_session.create_session()
    news = db_sess.query(News).all()

    data = []
    for new in news:
        author = db_sess.query(User).filter(User.id == new.author).first()
        author_name = f"{author.name} {author.surname}" if author else "Неизвестный автор"

        data.append({
            'Название': new.name,
            'Организатор': new.organizer,
            'Уровень': new.level,
            'Номинация': new.text,
            'Формат': new.format,
            'Ссылка на итоги конкурса': new.url,
            'Место проведения': new.place,
            'Дата проведения': new.date.strftime('%d.%m.%Y') if new.date else '',


        })

    df = pd.DataFrame(data)

    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Конкурсы', index=False)
    writer.close()
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='конкурсы.xlsx'
    )


@app.route('/all_students')
@login_required
def all_students():
    db_sess = db_session.create_session()

    # Получаем параметры фильтрации из запроса
    search_query = request.args.get('search', '').strip()
    contest_filter = request.args.get('contest', '').strip()
    place_filter = request.args.get('place', '').strip()

    # Создаем базовый запрос
    query = db_sess.query(Students)

    # Применяем фильтры
    if search_query:
        query = query.filter(Students.name.ilike(f'%{search_query}%'))
    if contest_filter:
        query = query.filter(Students.contest_id == contest_filter)
    if place_filter:
        query = query.filter(Students.place.ilike(f'%{place_filter}%'))

    students = query.all()

    # Получаем список всех конкурсов для фильтра
    contests = db_sess.query(News).all()

    return render_template(
        'all_students.html',
        students=students,
        contests=contests,
        search_query=search_query,
        contest_filter=contest_filter,
        place_filter=place_filter,
        title='Все участники'
    )


@app.route('/student_contests/<int:student_id>')
@login_required
def student_contests(student_id):
    db_sess = db_session.create_session()

    # Получаем информацию о студенте
    student = db_sess.query(Students).filter(Students.id == student_id).first()
    if not student:
        abort(404)

    # Получаем все конкурсы, в которых участвовал студент
    contests = db_sess.query(News).join(Students, News.id == Students.contest_id) \
        .filter(Students.name == student.name).all()

    return render_template(
        'student_contests.html',
        student=student,
        contests=contests,
        title=f'Конкурсы участника {student.name}'
    )


@app.route('/c')
def c():
    db_sess = db_session.create_session()
    contest_id = request.args.get('contest_id', type=int)

    if contest_id:
        students = db_sess.query(Students).filter(Students.contest_id == contest_id).all()
        contest = db_sess.query(News).filter(News.id == contest_id).first()
        contest_name = contest.name if contest else "Неизвестный конкурс"
    else:
        students = []
        contest_name = "Все участники"

    return render_template(
        'c.html',
        students=students,
        title=f'Участники конкурса: {contest_name}',
        contest_id=contest_id
    )


@app.route('/uchreg', methods=['GET', 'POST'])
@login_required
def uchreg():
    contest_id = request.args.get('contest_id', type=int)
    db_sess = db_session.create_session()

    if request.method == 'POST':
        name = request.form.get('name')
        place = request.form.get('place')
        contest_id = request.form.get('contest_id', type=int)

        if name and place and contest_id:
            student = Students(
                name=name,
                place=place,
                author=current_user.id,
                contest_id=contest_id
            )
            db_sess.add(student)
            db_sess.commit()
            return redirect(f'/c?contest_id={contest_id}')

    return render_template(
        'uchreg.html',
        title='Регистрация участников',
        contest_id=contest_id
    )


@app.route('/', methods=['GET', 'POST'])
def first():
    db_sess = db_session.create_session()
    text = ''
    search_query = request.args.get('search', '').strip()
    organizer_filter = request.args.get('organizer', '').strip()
    level_filter = request.args.get('level', '').strip()
    format_filter = request.args.get('format', '').strip()
    place_filter = request.args.get('place', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()

    if request.method == 'POST':
        if 'confirm' in request.form:
            user = db_sess.query(User).filter(User.email == current_user.email).first()
            confirmation_code = serializer.dumps(user.id, salt='confirm-salt')
            confirm_url = f'{request.host}/confirm/{confirmation_code}'
            msg = MIMEText(f'''Подтвердите учетную запись от Gym17, перейдя по ссылке: {confirm_url}.\n 
                Если вы не отправляли запрос, игнорируйте это сообщение''', 'html')
            msg['Subject'] = 'Account Confirmation Required'
            msg['From'] = 'kvondeniz@yandex.ru'
            msg['To'] = user.email

            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login('kvondeniz@yandex.ru', 'hafg vjqg nywe khnu')
                server.sendmail('valerylarionov06@gmail.com', [user.email], msg.as_string())
                text = 'Зайдите на почту и подтвердите свою учетную запись в течение трёх минут'

    query = db_sess.query(News)

    if search_query:
        query = query.filter(News.name.ilike(f'%{search_query}%'))
    if organizer_filter:
        query = query.filter(News.organizer.ilike(f'%{organizer_filter}%'))
    if level_filter:
        query = query.filter(News.level.ilike(f'%{level_filter}%'))
    if format_filter:
        query = query.filter(News.format.ilike(f'%{format_filter}%'))
    if place_filter:
        query = query.filter(News.place.ilike(f'%{place_filter}%'))

    try:
        if date_from:
            date_from_obj = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            query = query.filter(News.date >= date_from_obj)
        if date_to:
            date_to_obj = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()
            query = query.filter(News.date <= date_to_obj)
    except ValueError:
        pass

    news = query.all()
    news = news[::-1]

    organizers = db_sess.query(News.organizer).distinct().all()
    levels = db_sess.query(News.level).distinct().all()
    formats = db_sess.query(News.format).distinct().all()
    places = db_sess.query(News.place).distinct().all()

    authors = []
    confirmed_check = []
    for new in news:
        author = db_sess.query(User).filter(User.id == new.author).first()
        if author:
            name = author.name
            surname = author.surname
            confirm = author.confirmed
            authors.append(f"{name} {surname}")
            confirmed_check.append(confirm)
        else:
            authors.append("Неизвестный автор")
            confirmed_check.append(False)

    info = {
        'news': news,
        'authors': authors,
        'confirm_check': confirmed_check,
        'search_query': search_query,
        'organizer_filter': organizer_filter,
        'level_filter': level_filter,
        'format_filter': format_filter,
        'place_filter': place_filter,
        'date_from': date_from,
        'date_to': date_to,
        'organizers': [org[0] for org in organizers if org[0]],
        'levels': [lvl[0] for lvl in levels if lvl[0]],
        'formats': [fmt[0] for fmt in formats if fmt[0]],
        'places': [plc[0] for plc in places if plc[0]],
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
        image = db_sess.query(Images).filter(Images.user_id == elem.author).first()
        if image:
            encoded_string = str(image.b64_image)
            encoded_string = encoded_string.replace("b'", '').replace("'", '')
            result_image.append(encoded_string)
        else:
            result_image.append('')

    return render_template('news.html', **info, title='Gym17', text=text, action='', image=result_image)



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
        if current_user.email == 'kvondeniz@yandex.ru':
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
            return render_template('confirmed_sms.html', title='Gym17', text='Неизвестная ошибка')
    except Exception as text:
        return render_template('confirmed_sms.html', title='Gym17',
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


        user = User(
            name=name,
            surname=surname,
            email=form.email.data,
            age=form.age.data,
            city=city,

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

    with smtplib.SMTP('kvondeniz@yandex.ru', 587) as server:
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




@app.route('/help')
def help_handler():
    return render_template('help.html')


if __name__ == '__main__':
    main()
