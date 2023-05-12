import psycopg2
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = '3d78b91f1e25e9a8dc2d7516871ff74e'
connect = psycopg2.connect("dbname=postgres user=USERNAME")


@app.route('/')
def main():
    return render_template("main.html")


@app.route('/return')
def re_turn():
    return redirect(url_for('main'))


# 로그인
@app.route('/login', methods=['post'])
def login():
    cur = connect.cursor()
    cur2 = connect.cursor()
    id = request.form["id"]
    password = request.form["password"]
    send = request.form["send"]
    role = "tutor"

    cur.execute("SELECT * FROM users;")
    users = cur.fetchall()
    cur2.execute("SELECT * FROM account;")
    account = cur2.fetchall()

    # login 정보 확인
    if (id, password) in users:
        for row in account:
            if row[0] == id and row[3] == "tutee":
                role = "tutee"
                session['id'] = id
                session['role'] = role
                session['pw'] = password
                cur.close()
                cur2.close()
                return redirect(url_for('dashboard'))
        session['id'] = id
        session['role'] = role
        session['pw'] = password
        cur.close()
        cur2.close()
        return redirect(url_for('dashboard'))
    else:
        cur.close()
        cur2.close()
        return render_template("login_fail.html")


# 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user_pw = request.form['user_pw']
        role = request.form['role']

        # 중복 확인
        cur0 = connect.cursor()
        cur0.execute("SELECT id FROM users WHERE id=%s;", (user_id,))
        id_check = cur0.fetchone()
        cur0.close()

        # 회원가입 절차 진행
        if id_check is None:
            cur = connect.cursor()
            insert_user = "INSERT INTO users (id, password) VALUES (%s, %s);"
            cur.execute(insert_user, (user_id, user_pw))

            # 기본 설정 값
            DEFAULT_CREDIT = 10000
            DEFAULT_RATING = 'welcome'

            insert_account = "INSERT INTO account (id, credit, rating, role) VALUES (%s, %s, %s, %s)"
            cur.execute(insert_account, (user_id, DEFAULT_CREDIT, DEFAULT_RATING, role))
            connect.commit()

            session['id'] = user_id
            session['role'] = role
            cur.close()
            return redirect(url_for('dashboard'))

        return render_template('id_collision.html')
    else:
        return render_template('register.html')


# 대쉬보드
@app.route('/dashboard')
def dashboard():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    user_id = session['id']
    role = session['role']

    # 사용자 정보 가져오기
    cur = connect.cursor()
    cur.execute("SELECT credit, rating FROM account WHERE id = %s;", (user_id,))
    user_info = cur.fetchone()
    credit, rating = user_info
    cur.close()

    # rating color 불러오기
    curc = connect.cursor()
    curc.execute(
        "SELECT rating, condition, discount, color_r, color_g, color_b FROM rating_info;")
    rating_infos = [
        {'rating': rating, 'condition': condition, 'discount': discount, 'color_r': color_r, 'color_g': color_g,
         'color_b': color_b}
        for rating, condition, discount, color_r, color_g, color_b in curc.fetchall()]
    curc.close()

    rating_color = next((info for info in rating_infos if info['rating'] == rating), None)

    # 강의 목록 가져오기
    cur2 = connect.cursor()
    cur2.execute("SELECT code, name, price, tutor FROM lecture;")
    lectures = cur2.fetchall()
    lectures = [{'code': code, 'name': name, 'price': price, 'tutor': tutor} for code, name, price, tutor in lectures]
    cur2.close()

    # 수강 중인 강의 가져오기
    cur3 = connect.cursor()
    cur3.execute(
        'SELECT subject_name, lecture_name, e.tutor, price FROM enrollment AS e, lecture AS l, subject AS s WHERE tutee = %s and (e.code, e.lecture_name, e.tutor, e.lecture_price) = (l.code, l.name, l.tutor, l.price) and e.code = s.code;',
        (user_id,))
    enrolled_courses = cur3.fetchall()
    enrolled_courses = [{'subject': subject_name, 'lecture_name': lecture_name, 'tutor': tutor, 'price': price} for
                        subject_name, lecture_name, tutor, price in enrolled_courses]
    cur3.close()

    # 인기 과목 가져오기
    cur4 = connect.cursor()
    cur4.execute("""
                    with subject_count as (
                        select subject_name, count(all tutee) 
                        from subject natural join enrollment 
                        group by subject_name
                    )
                    select subject_name from subject_count 
                    where count = (select max(count) from subject_count);
                """)
    popular_subjects = [row[0] for row in cur4.fetchall()]
    cur4.close()

    # 인기 강의 가져오기
    cur5 = connect.cursor()
    cur5.execute("""
                    with lecture_count as (
                        select lecture_name, count(all tutee) 
                        from enrollment 
                        group by lecture_name, lecture_price, tutor, code
                    )
                    select lecture_name from lecture_count 
                    where count = (select max(count) from lecture_count);
                """)
    popular_lectures = [row[0] for row in cur5.fetchall()]
    cur5.close()

    # 인기 강사 가져오기
    cur6 = connect.cursor()
    cur6.execute("""
                    with tutor_count as (
                        select tutor, count(all tutee) 
                        from enrollment 
                        group by tutor
                    )
                    select tutor from tutor_count 
                    where count = (select max(count) from tutor_count);
                """)
    popular_tutors = [row[0] for row in cur6.fetchall()]
    cur6.close()

    my_courses = []
    if role == 'tutor':
        cur7 = connect.cursor()
        cur7.execute("""
            SELECT subject_name, lecture_name, tutee, lecture_price
            FROM subject NATURAL JOIN enrollment
            WHERE tutor = %s;
        """, (user_id,))
        my_courses = [
            {'subject_name': subject_name, 'lecture_name': lecture_name, 'tutee': tutee, 'lecture_price': lecture_price}
            for subject_name, lecture_name, tutee, lecture_price in cur7.fetchall()]
        cur7.close()

    return render_template('dashboard.html',
                           id=user_id, role=role, credit=user_info[0], rating=user_info[1],
                           rating_color=rating_color,
                           enrolled_courses=enrolled_courses, lectures=lectures,
                           popular_subjects=popular_subjects, popular_lectures=popular_lectures,
                           popular_tutors=popular_tutors,
                           my_courses=my_courses)


# 코스 등록 창
@app.route('/register_course', methods=['GET'])
def register_course():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    cur = connect.cursor()
    cur.execute("SELECT code, subject_name FROM subject;")
    subjects = cur.fetchall()
    subjects = [{'code': code, 'subject_name': subject_name} for code, subject_name in subjects]
    cur.close()

    return render_template('register_course.html', subjects=subjects)


# 코스 등록 진행
@app.route('/register_course_confirm', methods=['POST'])
def register_course_confirm():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    code = request.form['code']
    name = request.form['name']
    price = request.form['price']
    tutor = session['id']

    # 강의 추가
    cur = connect.cursor()
    cur.execute("INSERT INTO lecture (code, name, price, tutor) VALUES (%s, %s, %s, %s);",
                (code, name, price, tutor))
    connect.commit()
    cur.close()

    return redirect(url_for('dashboard'))


# 중복 강의 확인
def check_duplicate_flag(selected_courses, enrolled_courses):
    for selected_course in selected_courses:
        for enrolled_course in enrolled_courses:
            if selected_course == enrolled_course:
                return 1
    return 0


# 강사 자신의 강의인지 확인
def check_teach_myself_flag(selected_courses, user_id):
    tutor_list = []
    for selected_course in selected_courses:
        tutor_list.append(selected_course['tutor'])
    if user_id in tutor_list:
        return 1
    return 0


# 레이팅 업데이트 (크레딧 변동시)
def update_rating(user_id):
    cur = connect.cursor()
    cur.execute("UPDATE account SET rating='welcome' WHERE credit>=0 AND id = %s;"
                "UPDATE account SET rating='bronze' WHERE credit>=50000 AND id = %s;"
                "UPDATE account SET rating='silver' WHERE credit>=100000 AND id = %s;"
                "UPDATE account SET rating='gold' WHERE credit>=500000 AND id = %s;",
                (user_id, user_id, user_id, user_id))
    connect.commit()
    cur.close()
    return


# 코스 구매 창
@app.route('/purchase_courses', methods=['POST'])
def purchase_courses():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    user_id = session['id']

    # 선택한 강좌 가져오기
    selected_courses_data = request.form.getlist('selected_courses')
    selected_courses = []
    for course_data in selected_courses_data:
        code, name, price, tutor = course_data.split('|')
        course = {"code": code, "name": name, "tutor": tutor, "price": float(price)}
        selected_courses.append(course)

    # 듣고 있는 강좌 가져오기
    cur = connect.cursor()
    cur.execute("SELECT code, lecture_name, tutor, lecture_price FROM enrollment WHERE tutee = %s;", (user_id,))
    enrolled_courses = cur.fetchall()
    enrolled_courses = [{'code': code, 'name': lecture_name, 'tutor': tutor, 'price': lecture_price} for
                        code, lecture_name, tutor, lecture_price in enrolled_courses]
    cur.close()

    # 중복 강의 확인
    duplicate_flag = check_duplicate_flag(selected_courses, enrolled_courses)

    # 강사 자신의 강의인지 확인
    teach_myself_flag = check_teach_myself_flag(selected_courses, user_id)

    # selected_courses를 튜플의 리스트로 변환
    cur = connect.cursor()
    selected_courses_tuples = [(c['code'], c['name'], c['price'], c['tutor']) for c in selected_courses]
    cur.execute("SELECT code, name, price, tutor FROM lecture WHERE (code, name, price, tutor) IN %s;",
                (tuple(selected_courses_tuples),))
    selected_lectures = cur.fetchall()
    selected_lectures = [{'code': code, 'name': name, 'price': price, 'tutor': tutor} for code, name, price, tutor in
                         selected_lectures]
    cur.close()

    # 사용자 정보 가져오기
    cur2 = connect.cursor()
    cur2.execute("SELECT credit, rating FROM account WHERE id = %s;", (user_id,))
    user_info = cur2.fetchone()
    credit, rating = user_info
    cur2.close()

    # 할인율 가져오기
    cur3 = connect.cursor()
    cur3.execute("SELECT discount FROM rating_info WHERE rating = %s;", (rating,))
    discount_rate = cur3.fetchone()[0]
    cur3.close()

    # 총 가격, 할인된 가격 및 최종 가격 계산
    total_price = sum([lecture['price'] for lecture in selected_lectures])
    discounted_price = total_price * (1 - discount_rate / 100)
    final_price = round(discounted_price, 2)

    # 최종 가격 > 잔고 확인
    not_enough_balance_flag = 0
    if final_price > credit:
        not_enough_balance_flag = 1

    return render_template('purchase_courses.html', selected_courses=selected_lectures, credit=credit, rating=rating,
                           total_price=total_price, discounted_price=discounted_price, final_price=final_price,
                           duplicate_flag=duplicate_flag, teach_myself_flag=teach_myself_flag,
                           not_enough_balance_flag=not_enough_balance_flag)


@app.route('/confirm_purchase', methods=['POST'])
def confirm_purchase():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    user_id = session['id']

    final_price = float(request.form['final_price'])
    selected_courses_data = request.form.getlist('selected_courses')

    # 사용자의 credit에서 final_price 차감
    cur = connect.cursor()
    cur.execute("UPDATE account SET credit = credit - %s WHERE id = %s;", (final_price, user_id))
    connect.commit()

    # 선택한 강좌들을 enrollment 테이블에 추가
    selected_courses = []
    for course_data in selected_courses_data:
        code, name, price, tutor = course_data.split('|')
        selected_courses.append((user_id, tutor, code, name, float(price)))

    cur.executemany(
        "INSERT INTO enrollment (tutee, tutor, code, lecture_name, lecture_price) VALUES (%s, %s, %s, %s, %s);",
        selected_courses)
    connect.commit()
    cur.close()

    # tutor에게 크레딧 가산
    lecture_price_and_tutor = [(course[4], course[1]) for course in selected_courses]
    cur2 = connect.cursor()
    cur2.executemany(
        "UPDATE account SET credit = credit + %s WHERE id = %s;",
        lecture_price_and_tutor
    )
    connect.commit()
    cur2.close()

    # 레이팅 업데이트
    update_rating(user_id)
    for course in lecture_price_and_tutor:
        update_rating(course[1])

    return redirect(url_for('dashboard'))


@app.route('/cancel_purchase', methods=['POST'])
def cancel_purchase():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    session['selected_courses'] = []
    return redirect(url_for('dashboard'))


@app.route('/add_credit')
def add_credit():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    user_id = session['id']

    # credit, rating 표시

    cur = connect.cursor()
    cur.execute("SELECT credit, rating FROM account WHERE id = %s;", (user_id,))
    user_info = cur.fetchone()
    credit, rating = user_info
    cur.close()

    # rating color 불러오기
    cur2 = connect.cursor()
    cur2.execute(
        "SELECT rating, condition, discount, color_r, color_g, color_b FROM rating_info;")
    rating_infos = [
        {'rating': rating, 'condition': condition, 'discount': discount, 'color_r': color_r, 'color_g': color_g,
         'color_b': color_b}
        for rating, condition, discount, color_r, color_g, color_b in cur2.fetchall()]
    cur2.close()

    rating_color = next((info for info in rating_infos if info['rating'] == rating), None)

    return render_template('add_credit.html', id=user_id, credit=credit, rating=rating, rating_infos=rating_infos,
                           rating_color=rating_color)


@app.route('/confirm_add_credit', methods=['POST'])
def confirm_add_credit():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    user_id = session['id']
    credit_amount = int(request.form['credit_amount'])

    cur = connect.cursor()
    cur.execute("UPDATE account SET credit = credit + %s WHERE id = %s;", (credit_amount, user_id))
    connect.commit()
    cur.close()

    update_rating(user_id)

    return redirect(url_for('dashboard'))


@app.route('/user_info')
def user_info():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    if session.get('id') == 'admin':
        cur = connect.cursor()
        cur.execute("SELECT * FROM account NATURAL JOIN users ORDER BY ID asc;")
        users = [
            {'id': id, 'credit': credit, 'rating': rating, 'role': role, 'password': password}
            for id, credit, rating, role, password in cur.fetchall()]
        return render_template('user_info.html', users=users)
    else:
        return redirect(url_for('dashboard'))


@app.route("/enroll_info")
def enroll_info():
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    if session['id'] != 'admin':
        return redirect(url_for('dashboard'))

    cur = connect.cursor()
    cur.execute("SELECT * FROM enrollment;")
    enrollments = [
        {'tutee': tutee, 'tutor': tutor, 'code': code, 'lecture_name': lecture_name, 'lecture_price': lecture_price}
        for tutee, tutor, code, lecture_name, lecture_price in cur.fetchall()]
    cur.close()
    return render_template("enroll_info.html", enrollments=enrollments)


@app.route("/delete_enroll/<string:tutee>/<string:tutor>/<string:code>/<string:lecture_name>/<string:lecture_price>")
def delete_enroll(tutee, tutor, code, lecture_name, lecture_price):
    # 예외처리
    if 'id' not in session:
        return redirect(url_for('main'))

    if session['id'] != 'admin':
        return redirect(url_for('dashboard'))

    cur = connect.cursor()
    cur.execute(
        "DELETE FROM enrollment WHERE tutee=%s AND tutor=%s AND code=%s AND lecture_name=%s AND lecture_price=%s;",
        (tutee, tutor, code, lecture_name, lecture_price))
    connect.commit()
    cur.close()
    return redirect(url_for('enroll_info'))


# 크레딧 고치기
@app.route('/edit_credit', methods=['POST'])
def edit_credit():
    user_id = request.form['user_id']
    new_credit = request.form['new_credit']

    # Update user credit
    cur = connect.cursor()
    cur.execute("UPDATE account SET credit = %s WHERE id = %s;", (new_credit, user_id))

    connect.commit()
    cur.close()

    update_rating(user_id)

    return redirect(url_for('user_info'))


# 비밀번호 초기화
@app.route('/reset_password', methods=['POST'])
def reset_password():
    user_id = request.form['user_id']

    # Reset user password in the database
    cur = connect.cursor()
    cur.execute("UPDATE users SET password = '0000' WHERE id = %s;", (user_id,))

    # Commit the transaction and close the cursor
    connect.commit()
    cur.close()

    return redirect(url_for('user_info'))


# 유저 삭제
@app.route('/delete_user', methods=['POST'])
def delete_user():
    user_id = request.form['user_id']
    cur = connect.cursor()
    cur.execute("DELETE FROM enrollment WHERE tutor = %s OR tutee = %s;", (user_id, user_id))
    cur.execute("DELETE FROM lecture WHERE tutor = %s;", (user_id,))
    cur.execute("DELETE FROM account WHERE id = %s;", (user_id,))
    cur.execute("DELETE FROM users WHERE id = %s;", (user_id,))
    connect.commit()
    cur.close()
    return redirect(url_for('user_info'))


# 코스 삭제
@app.route('/delete_course', methods=['POST'])
def delete_course():
    if session['id'] == "admin":
        course_info = request.form['delete_course_info'].split('|')
        code, name, price, tutor = course_info

        cur = connect.cursor()
        cur.execute("DELETE FROM enrollment WHERE code=%s AND lecture_name=%s AND lecture_price=%s AND tutor=%s;",
                    (code, name, price, tutor))
        cur.execute("DELETE FROM lecture WHERE code=%s AND name=%s AND price=%s AND tutor=%s;",
                    (code, name, price, tutor))
        connect.commit()
        cur.close()

    return redirect(url_for('dashboard'))


# 로그아웃
@app.route('/logout')
def logout():
    session.pop('id', None)
    session.pop('role', None)
    return redirect(url_for('main'))


if __name__ == '__main__':
    app.run()
