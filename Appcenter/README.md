## AppCenter (Django)

### Nima qiladi
- `installers/` papkadagi barcha `.exe` va `.msi` fayllarni saytda roʻyxat qilib ko‘rsatadi.
- Bosilganda faylni yuklab beradi.
- PostgreSQL’da **qo‘shilgan vaqt** (`added_at`) va **download soni** (`download_count`) saqlanadi.

### Ishga tushirish
1) PostgreSQL serverini ishga tushiring (masalan, local yoki cloud).

2) Python paketlar:

```bash
python -m pip install -r requirements.txt
```

3) Migratsiyalar:

```bash
python manage.py migrate
```

4) Serverni ishga tushirish:

```bash
python manage.py runserver 0.0.0.0:8080
```

3) Migratsiya:

```bash
python manage.py migrate
```

4) `installers/` papkaga `.exe`/`.msi` fayllarni joylang.

5) Server:

```bash
python manage.py runserver 0.0.0.0:8080
```

Keyin brauzerda: `http://127.0.0.1:8080/`

### Postgres sozlamalari (default)
- DB: `appcenter`
- User: `appcenter`
- Password: `0711`
- Host: `127.0.0.1`
- Port: `5432`

Istasangiz env orqali o‘zgartirasiz:
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`.
