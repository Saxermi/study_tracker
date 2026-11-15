# ChatGPT-Prompt: Exercise-Feedback im exakt gültigen JSON-Format (Deutsch)

Kopiere diese Anweisung und füge die Aufgabenstellung, deine Lösung und den relevanten Chat an. Die KI bewertet nur tatsächlich belegte Vorgänge; ohne ausreichende Evidenz muss sie Werte offenlassen.

## Verbindlicher Ausgabe-Vertrag

**Verbindliche Ausgabe:** Antworte mit GENAU EINEM kopierbaren JSON-Codeblock mit Sprachkennung json und OHNE Text davor oder danach. Im Codeblock steht genau ein gültiges JSON-Objekt. In einer gespeicherten .json-Datei stehen KEINE Markdown-Codezäune.
**Typen und erlaubte Werte (Gross-/Kleinschreibung exakt; Feldnamen bleiben Englisch):**
- **difficulty:** JSON-Ganzzahl 1, 2, 3, 4 oder 5 (niemals Wörter wie high/medium/low, keine Dezimalzahlen, Prozentwerte oder 0); bei unklarer Grundlage null.
- **Schwierigkeitsmaßstab für das aktuelle Kursniveau:** 1 = sehr direktes Abrufen/Einsetzen ohne viel Schlussfolgern; 2 = bekannte Standardmethode mit wenigen Schritten; 3 = mittelschwere mehrstufige Aufgabe mit Entscheidungen oder Kombination bekannter Ideen; 4 = schwere Aufgabe mit mehreren nicht offensichtlichen Entscheidungen, Beweis oder ausführlicher Fehlersuche; 5 = besonders anspruchsvolle, ungewohnte Synthese mit viel eigenständigem Denken. Nicht anhand der erhaltenen Hilfe bewerten.
- **outcome:** genau "correct", "partial" oder "incorrect" als JSON-String, sonst null. Ohne sichtbare Lösung bzw. Überprüfung keine Behauptung über Korrektheit.
- **issue:** genau ein primärer Code aus concept, approach, calculation, implementation, instructions, careless, time, verification als JSON-String oder null. Keine freien Beschreibungen.
- **issues:** JSON-Liste mit 0–3 UNTERSCHIEDLICHEN Strings aus denselben acht Codes; [] bedeutet keine belegten Probleme. Wenn issue gesetzt ist, muss es in issues enthalten sein.
- **help_total:** JSON-Ganzzahl von 0 bis 5 oder null: Hilfe aus ALLEN Quellen. **help_chatgpt:** JSON-Ganzzahl 0 bis 5 oder null: nur ChatGPT-Hilfe; bei beiden Zahlen muss help_chatgpt <= help_total gelten.
- **Hilfeskala (beide Felder):** 0 = keine Hilfe, 1 = winziger Hinweis/Kontrolle, 2 = etwas Anleitung, 3 = mehrere substanzielle Hinweise/Erklärungen, 4 = umfangreiche schrittweise Hilfe, 5 = fast vollständiger Lösungsweg bzw. Lösung geliefert. Keine Wörter wie high/low als JSON-Werte.
- **chatgpt_interventions:** JSON-Liste von 0–3 UNTERSCHIEDLICHEN Strings aus verification, hint, guiding_questions, concept_explanation, approach_selection, step_by_step, debugging, calculation, code_generation, full_solution, error_identification; [] wenn unbelegt. Keine deutschen Anzeigenamen als Werte.
- **strength:** ein konkreter belegbarer Satz als JSON-String mit MAXIMAL 200 Zeichen oder null; **weakness:** ebenfalls maximal 200 Zeichen oder null.
- **skill_gap:** konkrete Kompetenzlücke als JSON-String mit MAXIMAL 100 Zeichen oder null; **next_action:** konkreter Übungsschritt als JSON-String mit MAXIMAL 160 Zeichen oder null.
- Gib alle 11 Schlüssel aus dem Beispiel aus; keine neuen oder übersetzten Schlüssel. Texte mit doppelten JSON-Anführungszeichen, null ohne Anführungszeichen, Listen in eckigen Klammern; keine Kommentare, zusätzlichen Kommata oder weiteren Text.
- Erfinde weder Stärke, Schwäche, Fehler, Ergebnis, Schwierigkeit noch Hilfe. Fehlende Evidenz -> null für einzelne Werte, [] für Problem-/Hilfelisten.

## Beispiel: gültiges, direkt kopierbares JSON

```json
{
  "difficulty": 3,
  "outcome": "partial",
  "issue": "approach",
  "issues": [
    "approach",
    "concept"
  ],
  "help_total": 4,
  "help_chatgpt": 4,
  "chatgpt_interventions": [
    "guiding_questions",
    "concept_explanation"
  ],
  "strength": "Ich habe die Nebenbedingungen selbst erkannt.",
  "weakness": "Ich brauchte Hilfe bei der Wahl der Pivotvariablen.",
  "skill_gap": "Pivotvariablen im Simplexverfahren bestimmen",
  "next_action": "Eine neue Pivotwahl-Aufgabe ohne Hinweise lösen."
}
```

## Grundlage für die Bewertung

Aufgabenstellung: [hier einfügen]
Eigene Lösung und wesentliche Zwischenschritte: [hier einfügen]
Relevanter Chat und Rückmeldung: [hier einfügen]

Das Ergebnis wird in StudyTracker als separate ChatGPT-Einschätzung gespeichert; die eigene Bewertung wird nicht automatisch überschrieben. Kein automatisches Speichern ganzer Chats und kein Verlauf mehrerer Lösungsversuche.
