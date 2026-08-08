# Let Us Dream Admin Platform

This repository is the clean foundation for the new Let Us Dream platform. It
currently contains only:

- administrator authentication by email/password;
- Google authentication for pre-authorized administrator accounts;
- a protected administrator dashboard;
- Django's built-in administration site for managing administrator accounts and
  Google OAuth configuration.

## Local setup

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Prepare the database and create the first administrator:

```bash
python manage.py migrate
python manage.py createsuperuser
```

Start the development server:

```bash
python manage.py runserver
```

The platform login is available at `/`, the authenticated dashboard at
`/dashboard/`, and Django administration at `/django-admin/`.

## Google authentication

Google sign-in remains available through `django-allauth`. Configure the Google
provider and credentials in Django administration. For security, a Google email
must already belong to an administrator account in the database; public account
creation is disabled.

## Tests

```bash
python manage.py test
```
