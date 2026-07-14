#!/bin/bash

echo "========================================"
echo "Sistema de Gestión de Mantenimiento"
echo "========================================"
echo ""

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no está instalado"
    exit 1
fi

echo "[1/3] Instalando dependencias Python..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Fallo al instalar dependencias"
    exit 1
fi

echo ""
echo "[2/3] Asegúrate de que MySQL esté ejecutándose"
echo "Por favor, importa el script database/schema.sql en MySQL o ejecuta:"
echo "mysql -u root -p gestion_mantenimiento < database/schema.sql"
echo ""
read -p "Presiona Enter cuando hayas completado la configuración de la base de datos..."

echo "[3/3] Iniciando la aplicación..."
echo ""
echo "La aplicación estará disponible en: http://localhost:5000"
echo ""

python3 app.py
