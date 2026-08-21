@echo off
:: Activar el entorno virtual
call newversion\Scripts\activate.bat

:: Ejecutar la aplicación de Streamlit
streamlit run route.py
