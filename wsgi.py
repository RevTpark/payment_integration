from .main import app

if __name__ == "__main__":
    app.secret_key = "some secret key"
    app.run()
