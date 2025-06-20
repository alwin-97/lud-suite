# LET US DREAM | Application Suite

## Developer Notes

### Python packages

Python packages that are required to run the project is been added into the requirements.txt file. The recommended way
to install the packages is to install the required packages in a virtual environment. To setup a virtual environment in
windows, follow the following steps.

    python.exe -m venv venv

We recommend to use the name for the environment as venv, which is also been excluded to be tracked in GitHub. Now to
install the required packages for the project, follow the command to install the required packages.

    pip install -r requirements.txt

Note, if there is an new package to be added to the project, install the package via pip command and then apply the pip
freeze command and redirect the output to the requirements.txt file for updating the requirements for all the
developers to be on the same page. The command to do the same is as follows:

    pip freeze > requirements.txt

After installing the packages you are ready to run the project in developer environment for project updates.

### Running the project

To run the django project we have to first ensure that we have the required migrations created and applied for the
database. The command to make the migrations and update the database structure for the project includes the following
steps.

1. Checking for migrations

         python manage.py makemigrations

2. Applying the migrations to database

         python manage.py migrate

Inorder to make the migrations apply, there should be migrations folder and the \____init____.py files to be present in
the apps that are present in the project, this folder and file might have been removed from tracking to GitHub.