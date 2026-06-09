import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tcms.settings.devel")
django.setup()

from google.cloud import firestore
db = firestore.Client(project="kiwi-tcms-d90e9")
for doc in db.collection("django_site").stream():
    print(f"Deleting {doc.id}")
    doc.reference.delete()
pk_str = str(1).zfill(20)  # gcloudc pads integer PKs to 20 chars
db.collection("django_site").document(pk_str).set({"domain": "127.0.0.1:8000", "name": "localhost"})
print("Done")
