# Let Us Dream Admin Platform

This repository is the clean foundation for the new Let Us Dream platform. It
currently contains only:

- administrator authentication by email/password;
- Google authentication for all pre-authorized platform users;
- a protected administrator dashboard and configuration portal;
- reusable locations, chapters, and three-year cohorts;
- cohort terms with multi-format materials (documents, images, and external URLs);
- shared images, videos and files at program, location, chapter and cohort levels;
- resource upload/view drawers with role-based access, parent-level sharing, and audit history;
- cohort-level Community Leader, Mentor, and Mentee role assignments;
- participant workspace displaying active cohort terms, syllabus documents, and learning resources;
- support for assigning multiple roles and cohorts to one user;
- Django's built-in administration site for managing administrator accounts and
  Google OAuth configuration.

## Local setup

Shared resources uploaded at program, location, chapter and cohort levels are
stored in `PRIVATE_RESOURCE_ROOT` (`private_resources/` by default). They are
downloaded through authenticated views, including video range requests. Keep
this directory outside public media/static hosting. Active members can read
resources in their groups and their parent levels; uploads and removal require
the relevant resource permission in a role assigned directly at that level.
Each uploaded file may be up to 100 MB (`RESOURCE_UPLOAD_MAX_BYTES`).

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
`/dashboard/`, application configuration at `/admin/configuration/`, user access
management at `/admin/users/`, and Django administration at `/django-admin/`.

For deployed environments, set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, and
`DJANGO_ALLOWED_HOSTS` (a comma-separated host list). The defaults are intended
for local development only.

## Google authentication

Google sign-in is provided through `django-allauth`. Configure the Google
provider and credentials in Django administration. For security, a Google email
must already belong to an active administrator or to a user with at least one
active cohort-role assignment; public account creation is disabled. Password
authentication is retained only as an administrator fallback.

## Tests

```bash
python manage.py test
```
