# ☁️ BookVoice-AI — Google Colab GPU Anleitung

**Kostenlose GPU für schnellere Hörbuch-Generierung**

---

## Was ist Google Colab?

Google Colab ist ein kostenloser Cloud-Service von Google.  
Du bekommst eine **GPU (T4)** — damit ist BookVoice-AI **10x schneller** als auf deinem PC!

| | Ohne GPU (CPU) | Mit GPU (Colab) |
|--|--|--|
| 1 Kapitel | ~16 Minuten | ~2 Minuten |
| 6 Kapitel | ~108 Minuten | ~9 Minuten |

---

## 📋 Schritt 1: Google Konto erstellen

1. Gehe zu **https://accounts.google.com**
2. Klick auf **"Konto erstellen"**
3. Folge den Anweisungen
4. ✅ Fertig — du hast jetzt 15 GB Google Drive kostenlos!

> **Tipp:** Erstelle ein **extra Konto nur für BookVoice-AI** — dann bleibt dein Drive sauber und du hast vollen Speicher für die KI-Modelle.

---

## 💾 Schritt 2: Google Drive für Modell-Speicherung

Beim ersten Start lädt Colab das KI-Modell herunter (~3 GB).  
Mit Drive-Speicherung passiert das **nur einmal** — danach startet es in Sekunden!

Das passiert automatisch wenn du das Notebook öffnest. ✅

---

## 🚀 Schritt 3: Colab starten

1. Klick auf diesen Link:  
   **[📓 BookVoice-AI Colab öffnen](https://colab.research.google.com/github/dolunay38/BookVoice-AI/blob/main/BookVoice_AI_Colab.ipynb)**

2. Oben rechts — mit deinem Google Konto anmelden

3. **GPU aktivieren:**  
   Menü → **Laufzeit** → **Laufzeittyp ändern** → **T4 GPU** auswählen → Speichern

4. **Schritt 0 ausführen** — Drive verbinden  
   ▶️ Play-Button klicken → Google Drive erlauben

5. **Schritt 1 ausführen** — Installation (beim ersten Mal ~15 Min, danach ~2 Min)  
   ▶️ Play-Button klicken → warten bis ✅ FERTIG!

6. **Schritt 2 ausführen** — Server starten  
   ▶️ Play-Button klicken → **URL kopieren** die erscheint

7. **Schritt 3 ausführen** — Session aktiv halten  
   ▶️ Play-Button klicken → **NICHT stoppen!**

---

## 🔗 Schritt 4: Mit BookVoice-AI verbinden

1. BookVoice-AI öffnen: **http://localhost:7502** (oder deine Server-Adresse)
2. Engine wählen: **☁️ GPU Colab**
3. URL einfügen die du aus Colab kopiert hast
4. **Verbinden** klicken
5. ✅ Grüner Punkt = verbunden!

---

## ⚠️ Wichtige Hinweise

### Session aktiv halten
- **Schritt 3 muss immer laufen!** Sonst trennt Colab nach 90 Minuten.
- Browser Tab **nicht schließen** während du generierst.
- Du kannst den **Laptop anlassen** — Colab läuft in der Cloud.

### Beim nächsten Mal
- Schritt 0: Drive verbinden ✅
- Schritt 1: Installation (~2 Min statt 15 Min dank Drive-Cache) ✅
- Schritt 2: Server starten ✅
- Schritt 3: Aktiv halten ✅

### Kostenlos-Limits
- ~4–5 Stunden GPU pro Tag kostenlos
- Danach kurz warten oder morgen weitermachen
- Für mehr: **Google Colab Pro** (~10€/Monat)

---

## ❓ Häufige Fragen

**Q: Muss ich etwas installieren?**  
A: Nein! Alles läuft im Browser.

**Q: Sind meine Daten sicher?**  
A: Deine Stimme und Texte werden nur während der Session verarbeitet — nichts wird dauerhaft gespeichert.

**Q: Was wenn die Verbindung abbricht?**  
A: Einfach Schritt 2 nochmal ausführen und neue URL in BookVoice-AI eingeben.

**Q: Funktioniert es auf dem Handy?**  
A: Colab auf dem Handy öffnen halten die Session aktiv — aber bedienen am besten am PC.

---

## 🆘 Hilfe

**GitHub:** https://github.com/dolunay38/BookVoice-AI

---

*BookVoice-AI · Google Colab Integration · Kostenlose GPU*
