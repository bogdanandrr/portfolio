# andrei-bogdan.work

## Structura

```
Website/
├── index.html                 homepage (lista de proiecte e generată automat)
├── contact.html
├── <proiect>.html             paginile proiectelor, generate automat — nu le edita de mână
├── update-content.command     dublu-click după ce schimbi ceva în projects/
├── projects/                  ← AICI lucrezi: un folder per proiect
├── assets/
│   ├── style.css              tot designul
│   ├── site.js                videouri (pornesc când apar pe ecran) + butonul de sunet
│   ├── fonts/                 Switzer
│   ├── images/                poza de profil, posterul videoului intro
│   ├── video/                 videoul intro
│   └── thumbs/                cadre din videourile proiectelor (generate automat)
└── scripts/
    └── build-projects.py      scriptul rulat de update-content.command
```

## Un proiect nou

1. Fă un folder în `projects/`, de ex. `15 Nume Proiect` (numărul dă ordinea și nu apare pe site).
2. Pune în el `poster` (imagine sau video), restul imaginilor/videourilor (`1.png`, `2.png`...) și, opțional:
   - `descriere.txt` — textul proiectului (rând gol = paragraf nou)
   - `real-poster` — dacă vrei pe homepage altceva decât pe pagina proiectului
3. Dublu-click pe `update-content.command`.

Fișierele mari se comprimă automat; originalele se mută în `../Website-originals/projects/`.
Pe homepage, la posterele verticale apar lângă și primele 2 imagini (`1`, `2`).

## Ce nu mai e folosit

Videourile vechi (`content/`) și paginile de branding au fost mutate în
`../Website-originals/archive/` — nu sunt șterse.
