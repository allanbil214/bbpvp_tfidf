requirements:
- pip install pandas numpy scikit-learn matplotlib Sastrawi openpyxl tkinter

# One Folder
'''
pyinstaller --noconfirm --onedir --windowed --icon "C:\Users\Allan\Documents\bbpvp_tfidf\app.ico" --add-data "C:\Users\Allan\AppData\Roaming\Python\Python314\site-packages\Sastrawi;Sastrawi/" --hidden-import "mysql.connector.plugins.mysql_native_password" --hidden-import "mysql.connector.locales.eng" --collect-all "mysql.connector"  "C:\Users\Allan\Documents\bbpvp_tfidf\app_v2.py"
'''

# One File
'''
pyinstaller --noconfirm --onefile --windowed --icon "C:\Users\Allan\Documents\bbpvp_tfidf\app.ico" --add-data "C:\Users\Allan\AppData\Roaming\Python\Python314\site-packages\Sastrawi;Sastrawi/" --hidden-import "mysql.connector.plugins.mysql_native_password" --hidden-import "mysql.connector.locales.eng" --collect-all "mysql.connector"  "C:\Users\Allan\Documents\bbpvp_tfidf\app_v2.py"
'''