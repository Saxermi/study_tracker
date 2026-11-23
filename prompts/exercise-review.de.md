# ChatGPT-Prompt: Übungsbewertung mit kalibrierter Hilfeskala

Diesen Prompt gemeinsam mit der tatsächlichen Aufgabe, deinen eigenen Lösungsschritten und dem relevanten Chat verwenden. Nur nachweisbare Unterstützung bewerten.

**Verbindliche Ausgabe:** Antworte mit GENAU EINEM kopierbaren JSON-Codeblock (`json`) OHNE Text davor oder danach. Darin steht ein gültiges JSON-Objekt. Als .json-Datei nur den Inhalt ohne Codezäune speichern.
**Exakte JSON-Typen und Werte (Schlüssel und Enum-Codes bleiben Englisch):**
- `difficulty`: JSON-GANZZAHL 1, 2, 3, 4 oder 5, oder null. 1 = direktes Abrufen/Einsetzen; 2 = bekannte Routineaufgabe; 3 = mittelschwer mit mehreren Schritten; 4 = schwierig mit nicht offensichtlichen Entscheidungen, Beweisen oder aufwendigem Debugging; 5 = außergewöhnliche unbekannte Synthese. Schwierigkeit der Aufgabe bewerten, NICHT die erhaltene Hilfe. Keine Strings wie "high".
- `outcome`: JSON-STRING exakt "correct", "partial" oder "incorrect", sonst null, wenn eine überprüfte Lösung fehlt.
- `issue`: genau EIN primärer JSON-STRING aus "concept", "approach", "calculation", "implementation", "instructions", "careless", "time", "verification", oder null.
- `issues`: JSON-LISTE mit 0–3 VERSCHIEDENEN Codes aus denselben acht Problemen. Falls `issue` gesetzt, muss es in `issues` enthalten sein. Sonst [] bei keinen beobachteten Problemen.
- `help_total`: JSON-GANZZAHL 0–5 oder null, für ALLE Hilfsquellen. `help_chatgpt`: JSON-GANZZAHL 0–5 oder null, nur für tatsächlich durch ChatGPT geleistete Hilfe. Wenn beide bekannt, muss `help_chatgpt` <= `help_total` gelten. Unbekannte andere Hilfsquellen NICHT automatisch als null oder ChatGPT-Hilfe bewerten.
- `chatgpt_interventions`: JSON-LISTE mit 0–3 VERSCHIEDENEN Strings aus "verification", "hint", "guiding_questions", "concept_explanation", "approach_selection", "step_by_step", "debugging", "calculation", "code_generation", "full_solution", "error_identification". Sonst []. Dies sind ARTEN der Hilfe, nicht ihre MENGE.
- `strength`: EIN belegter konkreter Satz als JSON-STRING mit max. 200 Zeichen, sonst null. `weakness`: ebenfalls max. 200 Zeichen oder null.
- `skill_gap`: konkrete Kompetenzlücke als kurzer JSON-STRING mit max. 100 Zeichen oder null. `next_action`: konkreter nächster Übungsschritt als JSON-STRING mit max. 160 Zeichen oder null.
- Genau ALLE ELF Felder ausgeben, keine weiteren Schlüssel. Strings in doppelten Anführungszeichen, Zahlen ohne Anführungszeichen, null ohne Anführungszeichen, Listen in eckigen Klammern. Keine Kommentare/überzählige Kommata; keine Vermutungen. Fehlender Einzelwert = null, unbelegte Listen = [].
**Hilfeskala — anhand des tatsächlichen Gesprächs kalibrieren (NICHT anhand der Chatlänge):**
0 = Keine Hilfe beim Lösen. Beispiel: Die Aufgabe wurde selbstständig ohne Assistent gelöst.
1 = Kontrolle oder winzige Klarstellung. Beispiel: Die eigene Lösung steht bereits fest und ChatGPT prüft nur das Resultat. Eine ausführliche NACHBESPRECHUNG macht daraus keine 4/5.
2 = Ein kleiner richtungsweisender Hinweis. Beispiel: ChatGPT weist auf Induktion oder eine passende Formel hin; der Lernende wählt den Lösungsweg, rechnet und schließt selbstständig ab.
3 = Mehrere gezielte Hinweise/Leitfragen. Beispiel: ChatGPT fragt nach einer Bedingung und macht auf einen Fehler aufmerksam; die wesentlichen Lösungsschritte stammen weiterhin vom Lernenden.
4 = Wesentliche Hilfe VOR dem selbstständigen Abschluss. Beispiel: ChatGPT liefert die entscheidende Methode UND mehrere zentrale Rechen-/Beweisschritte, während der Lernende einen bedeutenden Rest selbst fertigstellt.
5 = Nahezu vollständige oder vollständige Lösung VOR dem eigenen Lösungsversuch. Beispiel: ChatGPT schreibt den gesamten Beweis, Code oder Rechenweg, den der Lernende hauptsächlich übernimmt oder nur leicht korrigiert.
**Gegen Inflation:** Fünf Chat-Nachrichten sind NICHT automatisch 5/5. Viele Rückfragen, lange Gespräche, Konzept-Erklärungen NACH erfolgreicher Lösung und reine Antwortkontrolle sind nicht automatisch 4 oder 5. Für 4 müssen zentrale vom Assistenten gelieferte Lösungsschritte erkennbar sein; für 5 eine nahezu vollständige Lösung. Sind zwei benachbarte Werte möglich, wähle den NIEDRIGEREN durch Belege gestützten Wert; fehlt der Lösungsablauf, null. Eigenständige Schritte von ChatGPT-Beiträgen unterscheiden. Unbekannte externe Hilfen nicht erfinden.
**Vor der Ausgabe:** Gespräch mit den Beispielen 0–5 abgleichen; entscheidende Hilfe VOR der eigenständigen Lösung identifizieren. Werte aus dem JSON-Muster NICHT kopieren. Nur JSON-Codeblock ausgeben.

## Beispiel (fiktiv – Bewertungen NICHT kopieren)

```json
{
  "difficulty": 3,
  "outcome": "partial",
  "issue": "approach",
  "issues": [
    "approach"
  ],
  "help_total": 2,
  "help_chatgpt": 2,
  "chatgpt_interventions": [
    "hint"
  ],
  "strength": "Ich habe die Gleichungen selbst aufgestellt.",
  "weakness": "Für den nächsten Schritt brauchte ich einen Hinweis.",
  "skill_gap": "Passende Umformung auswählen",
  "next_action": "Eine ähnliche Umformung ohne Hinweise lösen."
}
```

## Auszuwertende Informationen

Aufgabenstellung: [hier einfügen]
Eigene Lösungsversuche und wesentliche Zwischenschritte: [hier einfügen]
Chatverlauf inkl. Zeitpunkt des selbstständigen Abschlusses: [hier einfügen]

Studienprofil speichert GPT-Feedback getrennt von der eigenen Bewertung. Weder Chatverlauf noch mehrere Versuche werden automatisch gespeichert.
