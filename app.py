from flask import Flask, flash, render_template, url_for, request, redirect, abort, send_from_directory, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_user, LoginManager, UserMixin, logout_user, login_required
from flask_migrate import Migrate
import os
import io
from PIL import Image
from imghdr import what
from datetime import datetime
from werkzeug.utils import secure_filename



base_dir = os.path.dirname(os.path.realpath(__file__))

app = Flask(__name__)

UPLOAD_PATH = os.path.join(app.root_path, 'static', 'uploads')

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///' + os.path.join(base_dir,'users.db')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = '4d4c18d8d33c8c704705'
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.png', '.gif']
app.config['UPLOAD_PATH'] = UPLOAD_PATH

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)

def create_tables():
    db.create_all()

class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer(), primary_key=True)
    username = db.Column(db.String(255), nullable=False, unique=True)
    first_name = db.Column(db.String(50), nullable =False)
    last_name = db.Column(db.String(50), nullable =False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    img_user_view = db.Column(db.String(255), nullable=True)  
    image_mime_type = db.Column(db.String(50), nullable=True)
    password_hash =  db.Column(db.Text(), nullable=False)

    def __repr__(self):
        return f'User<{self.username}>'

class Blogpost(db.Model):
    __tablename__ = 'blogpost'
    id = db.Column(db.Integer(), primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    author = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False)
    img_post_view = db.Column(db.String(255), nullable=True)  
    image_mime_type = db.Column(db.String(50), nullable=True) 
    created_at = db.Column(db.DateTime, default= datetime.utcnow)
    comments = db.relationship('Comment', backref='post', lazy=True)
    

class Comment(db.Model):
    __tablename__ = 'comment'
    id = db.Column(db.Integer(), primary_key=True)
    author = db.Column(db.String(50))
    content = db.Column(db.Text, nullable=False) 
    created_at = db.Column(db.DateTime, default= datetime.utcnow)
    post_id = db.Column(db.Integer, db.ForeignKey('blogpost.id'), nullable=False)

@login_manager.user_loader
def user_loader(id):
    return User.query.get(int(id))

#route to home page
@app.route('/')
def index():
    posts = Blogpost.query.all()
    users = User.query.all()

    context = {
        'posts': posts,
        'users':users
    }
    
    return render_template ("index.html", **context)

def validate_image(stream):
    try:
        # S'assurer que le pointeur est au début
        stream.seek(0)
        # Lire les données du flux
        image_data = stream.read()
        if not image_data:
            print("Error in validate_image: Empty image data")
            return False
        # Vérifier que les données sont bien des bytes
        if not isinstance(image_data, bytes):
            print(f"Error in validate_image: Data is not bytes, got {type(image_data)}")
            return False, None

        # Utiliser imghdr.what() pour détecter le format de l'image
        image_format = what(None, image_data)
        if image_format not in ('jpeg', 'png', 'gif'):  # Formats supportés
            print(f"Error in validate_image: Unsupported image format: {image_format}")
            return False, None
        
        # Charger les données dans un BytesIO pour Pillow
        image_stream = io.BytesIO(image_data)
        img = Image.open(image_stream)
        img.verify()  # Valide l'image
        img.close()
        print("Image validated successfully")
        return True, image_data
    except Exception as e:
        print(f"Error in validate_image: {str(e)}")
        return False, None


@app.route('/', methods=['POST'])
def upload_files():
    uploaded_file = request.files['file']
    filename = secure_filename(uploaded_file.filename)
    if filename != '':
        file_ext = os.path.splitext(filename)[1]
        is_valid, _ = validate_image(uploaded_file.stream)
        if file_ext not in app.config['UPLOAD_EXTENSIONS'] or not is_valid:
            abort(400)

        uploaded_file.save(os.path.join(app.config['UPLOAD_PATH'], filename))
    return redirect(url_for('index'))

@app.route('/image/<int:post_id>')
def serve_image(post_id):
    post = Blogpost.query.get_or_404(post_id)
    if not post.img_post_view:
        abort(404, description="No image available for this post")
    
    filepath = os.path.join(app.config['UPLOAD_PATH'], post.img_post_view)

    if not os.path.exists(filepath):
        abort(404, description="Image file not found")

    return send_file(filepath, mimetype='image/jpeg')

@app.route('/user_image/<int:user_id>')
def serve_user_image(user_id):
    user = db.session.get(User, user_id)
    if not user or not user.img_user_view:
        abort(404, description="No profile image available")

    filepath = os.path.join(app.config['UPLOAD_PATH'], user.img_user_view)

    if not os.path.exists(filepath):
        abort(404, description="Image file not found")

    return send_file(filepath, mimetype='image/jpeg')
    
#to login an already existing user
@app.route('/login', methods = ['POST', 'GET'])
def login():
    #check if user has created an account
    username = request.form.get('username')
    password = request.form.get('password')

    user = User.query.filter_by(username = username).first()

    #checking if the username and the password are the same
    if user and check_password_hash(user.password_hash, password):
        print('pass----')
        login_user(user)
        return redirect(url_for('index'))

    return render_template('login.html')

#function to logout a user
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

#route for creating a new account page
@app.route('/signup', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST' :
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        #if it is the first time the user in doing this
        user = User.query.filter_by(username= username).first()
        if user :
            return redirect(url_for('register'))

        email_exists = User.query.filter_by(email=email).first()
        if email_exists:
            return redirect(url_for('register'))
        
        #generate password from password passed by user and generate a password and then save it inside password_hash
        password_hash = generate_password_hash(password)

        new_user = User(first_name = first_name, last_name = last_name, username = username, email = email, password_hash= password_hash)
        
        db.session.add(new_user) #add user to db
        db.session.commit() #save user to db

        #redirect to login page after user has been saved to the db
        return redirect(url_for('login'))
        
    return render_template('signup.html')

#route for contact page
@app.route('/contact')
def contact():
    return render_template('contact.html')


#route for profile page
@app.route('/edit_profile')
@login_required
def edit_profile():
    return render_template('profile.html', user=current_user)
    
#route for profile page
@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    # Recharger l'utilisateur depuis la base de données
    user = db.session.get(User, current_user.id)
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('profile'))

    if request.method == "POST":
        try:
            # Récupérer les données du formulaire
            username = request.form.get('username')
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            email = request.form.get('email')

            # Validation des champs obligatoires
            if not username or not email:
                flash('Username and email are required.', 'error')
                return redirect(url_for('profile'))

            if '@' not in email or '.' not in email:
                flash('Invalid email address.', 'error')
                return redirect(url_for('profile'))

            # Mise à jour des données
            user.username = username
            user.first_name = first_name
            user.last_name = last_name
            user.email = email

            # Upload d'image (optionnel)
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                filename = secure_filename(uploaded_file.filename)
                file_ext = os.path.splitext(filename)[1].lower()

                if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                    flash(f"Invalid file extension: {file_ext}", 'error')
                    return redirect(url_for('profile'))

                upload_path = app.config['UPLOAD_PATH']
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)

                filepath = os.path.join(upload_path, filename)
                uploaded_file.save(filepath)

                if not os.path.exists(filepath):
                    flash('Failed to save image to disk.', 'error')
                    return redirect(url_for('profile'))

                # Mise à jour du nom de fichier dans la base
                user.img_user_view = filename

            # Sauvegarder dans la base
            db.session.commit()
            flash('Your changes have been saved.', 'success')
            return redirect(url_for('profile'))

        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'error')
            return redirect(url_for('profile'))

    return render_template('profile.html', user=user)


#route for creating a new blog post page
@app.route ('/create_post')
def create_post():
    return render_template('create_post.html')

#function handling the addiion of a new blog post
@app.route('/create_post', methods = ['GET', 'POST'])
@login_required
def post():
    if request.method == 'POST':
        try:
            title = request.form.get('title')
            content = request.form.get('content')

            # Validation des champs requis
            if not title or not content:
                abort(400, description="Title and content are required")

            author = current_user.username
            filename = None  # Nom du fichier image, s’il y en a

            # Gestion du fichier uploadé
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                file_ext = os.path.splitext(uploaded_file.filename)[1].lower()

                if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                    abort(400, description="Invalid file extension")

                filename = secure_filename(uploaded_file.filename)
                upload_path = app.config['UPLOAD_PATH']

                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)

                filepath = os.path.join(upload_path, filename)
                uploaded_file.save(filepath)

                if not os.path.exists(filepath):
                    abort(500, description="Failed to save image to disk")

            # Création du post avec l’image (stockée par nom de fichier)
            post = Blogpost(
                title=title,
                author=author,
                content=content,
                img_post_view=filename,  # Stocker juste le nom de fichier
                created_at=datetime.utcnow()
            )

            db.session.add(post)
            db.session.commit()

            return redirect(url_for('index'))

        except Exception as e:
            db.session.rollback()
            abort(500, description=f"Error: {str(e)}")


#route for editing a post
@app.route('/update/<int:id>/', methods = ['GET', 'POST'])
@login_required
def update(id):
    post_to_update = Blogpost.query.get_or_404(id)

    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            title = request.form.get('title')
            content = request.form.get('content')

            # Validation des champs requis
            if not title or not content:
                abort(400, description="Title and content are required")

            # Mettre à jour les champs texte
            post_to_update.title = title
            post_to_update.content = content

            # Gestion du fichier uploadé (facultatif)
            uploaded_file = request.files.get('file')
            if uploaded_file and uploaded_file.filename:
                file_ext = os.path.splitext(uploaded_file.filename)[1].lower()

                # Vérification de l'extension
                if file_ext not in app.config['UPLOAD_EXTENSIONS']:
                    abort(400, description=f"Invalid file extension: {file_ext}")

                filename = secure_filename(uploaded_file.filename)
                upload_path = app.config['UPLOAD_PATH']

                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)

                filepath = os.path.join(upload_path, filename)
                uploaded_file.save(filepath)

                if not os.path.exists(filepath):
                    abort(500, description="Failed to save image to disk")

                # Mettre à jour le champ image (nom du fichier)
                post_to_update.img_post_view = filename

            # Commit dans la base de données
            db.session.commit()
            return redirect(url_for("index"))

        except Exception as e:
            db.session.rollback()
            abort(500, description=f"Error: {str(e)}")

    # Si la méthode est GET, afficher le formulaire de mise à jour
    context = {
        'post': post_to_update
    }
    return render_template('update_post.html', **context)


@app.route('/uploads/<filename>')
def upload(filename):
    return send_from_directory(app.config['UPLOAD_PATH'], filename)

#route for deleting a post
@app.route('/delete/<int:id>/', methods = ['GET'])
@login_required
def delete(id):
    posts_to_delete = Blogpost.query.get_or_404(id)

    db.session.delete(posts_to_delete)
    db.session.commit()

    return redirect(url_for('index'))

@app.route('/view_post/<int:id>/', methods = ['GET','POST'])
def view_post(id):
    post_to_view = Blogpost.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            content = request.form.get('content')
            if not current_user.is_authenticated:
                flash("You need to login to post a comment as a Member", "warning")
                return redirect(url_for("view_post",  id=post_to_view.id))
            
            author = current_user.username
            new_comment = Comment(post_id=post_to_view.id, author=author, content=content)
            db.session.add(new_comment)
            db.session.commit()
            flash("Your comment has been added to the post", "success")
            return redirect(url_for("view_post", id=post_to_view.id))
            
        except Exception as e:
            db.session.rollback()
            abort(500, description=f"Error: {str(e)}")
    
    context = {
        'post': post_to_view
    }

    return render_template('view_post.html', **context)
        

if __name__ == "__main__":
    app.run(debug=True)