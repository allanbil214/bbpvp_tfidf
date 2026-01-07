requirements:
- pip install pandas numpy scikit-learn matplotlib Sastrawi openpyxl tkinter

# One Folder
'''
pyinstaller --noconfirm --onedir --windowed --icon "C:\Users\Allan\Documents\bbpvp_tfidf\app.ico" --add-data "C:\Users\Allan\AppData\Roaming\Python\Python314\site-packages\Sastrawi;Sastrawi/" --hidden-import "mysql.connector.plugins.mysql_native_password" --hidden-import "mysql.connector.locales.eng" --collect-all "mysql.connector"  "C:\Users\Allan\Documents\bbpvp_tfidf\app_v2.py"
'''

# One File
'''
pyinstaller --noconfirm --onefile --windowed --icon "C:\Users\Allan\Documents\bbpvp_tfidf\app.ico" --add-data "C:\Users\Allan\AppData\Roaming\Python\Python314\site-packages\Sastrawi;Sastrawi/" --hidden-import "mysql.connector.plugins.mysql_native_password" --hidden-import "mysql.connector.locales.eng" --collect-all "mysql.connector"  "C:\Uirsers\Allan\Documents\bbpvp_tfidf\app_v2.py"
'''

# to-do
- tambah not all but few data to calculate all preprocessing and other stuff (added caching instead | done | desktop version)
- add progress bar (done | desktop version)
- fix weird column on view data especially on training (fixed | desktop version)
- show vector for text on view data?
- add some animation (web version)
- Tambahkan rekomendasi by training instead by job too (done | desktop version)
- Add scroll bar to left panel (done | desktop version only)