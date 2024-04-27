python .\manage.py makemigrations
python .\manage.py migrate
python manage.py spectacular --file schema.yml
openapi-generator-cli generate -i http://localhost:8000/api/schema/ -g typescript-fetch -o  D:\Programming\react-commerce\src\api