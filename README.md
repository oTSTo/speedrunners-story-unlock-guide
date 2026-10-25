# SpeedRunners — sblocco indicatori della storia (Windows / Steam)

**Ultima revisione: 25 ottobre 2026.**

Questa guida descrive una modifica locale al salvataggio per rendere dorati tutti e 16 gli indicatori della campagna mostrati nella schermata *Chapter Select* (4 capitoli × 4 indicatori). Il procedimento è stato verificato su un salvataggio Windows di SpeedRunners: dopo aver completato un livello in Facile, un singolo indicatore è cambiato da `01` a `04`; impostando allo stesso valore i 16 indicatori, il gioco li ha mostrati tutti dorati al successivo avvio.

È una tecnica sperimentale basata sul confronto dei salvataggi, non una funzione ufficiale né una specifica pubblicata dagli sviluppatori. Il test risale al 25 ottobre 2026; la versione/build del gioco non è stata registrata. Dopo un aggiornamento del gioco, ricontrollare il formato prima di applicarla.

## Cosa modifica

Lo script `unlock_story.py` legge un file `SpeedRunnerHDProgressionStore` in formato versione 5 e verifica che la struttura corrisponda a quella osservata. Cambia soltanto i 16 byte degli indicatori della storia, portandoli a `04`; gli XP restano invariati a meno che tu non specifichi `--add-xp` o `--set-xp`. Ricompense, impostazioni e `GameStore` non vengono modificati.

Lo script parte in modalità di sola lettura: mostra cosa cambierebbe, senza scrivere. Con `--apply` crea una copia `.bak` e poi modifica i file indicati. Se il file non corrisponde alla struttura attesa, si ferma senza modificarlo.

> L'uso di valori `04` è stato osservato funzionare nella prova descritta; non è garantito per tutte le versioni future. La modifica riguarda gli indicatori della storia visti nella schermata, non prova a sbloccare obiettivi Steam, contenuti online o altri elementi non verificati.

## Prima di iniziare

1. Chiudi completamente SpeedRunners.
2. Individua il salvataggio attivo e fanne una copia separata. Non usare un file grezzo trovato sul Desktop o un salvataggio di un altro profilo: in questa prova un file non compatibile ha causato il reset temporaneo delle statistiche.
3. Se Steam Cloud è attivo, tieni presente che Steam può sincronizzare i file prima e dopo una sessione. Per questo metodo è preferibile controllare entrambe le copie locali del file mentre il gioco è chiuso. La documentazione ufficiale di Steam descrive la sincronizzazione Cloud attorno alle sessioni di gioco: [Steam Cloud — Steamworks](https://partner.steamgames.com/doc/features/cloud).
4. Non procedere se la verifica preliminare dello script segnala versione o struttura inattesa.

## Posizioni da controllare

Le cartelle possono variare in base all'installazione. Per l'installazione Windows osservata, i due percorsi erano:

```text
%USERPROFILE%\Documents\SavedGames\SpeedRunners\CEngineStorage\AllPlayers\SpeedRunnerHDProgressionStore_<SteamID64>
<cartella Steam>\userdata\<SteamID3>\207140\remote\SpeedRunnerHDProgressionStore
```

`<SteamID64>` e `<SteamID3>` sono segnaposto: non copiarli letteralmente. Usa i valori del tuo profilo e la cartella Steam effettiva. Se uno dei due file non esiste, non inventarlo: lavora solo sui file presenti e identificati come salvataggio di SpeedRunners.

## Procedura

Serve Python 3; lo script usa solo la libreria standard.

1. Scarica `unlock_story.py` dalla repository e apri PowerShell nella cartella in cui l'hai salvato.
2. Sostituisci i percorsi segnaposto con i tuoi percorsi reali. Prima fai una prova in sola lettura:

```powershell
py .\unlock_story.py --dry-run "<percorso del file locale>" "<percorso del file Steam remote>"
```

Per aggiungere 10.000 XP, aggiungi `--add-xp 10000` al comando. Per impostare un totale preciso, usa `--set-xp` al posto di `--add-xp`. Ad esempio, nel salvataggio testato il gioco mostrava `MAX` con 100277 XP: è un valore osservato su quell'installazione, non un limite universale verificato.

```powershell
py .\unlock_story.py --dry-run --add-xp 10000 "<percorso del file locale>" "<percorso del file Steam remote>"
```

3. Controlla che lo script riconosca versione 5, quattro capitoli e quattro indicatori per capitolo. Se l'output segnala una struttura inattesa, fermati.
4. Solo dopo la verifica, applica la modifica agli stessi file:

```powershell
py .\unlock_story.py --apply "<percorso del file locale>" "<percorso del file Steam remote>"
```

Per applicare anche l'aumento di 10.000 XP, usa invece:

```powershell
py .\unlock_story.py --apply --add-xp 10000 "<percorso del file locale>" "<percorso del file Steam remote>"
```

Se preferisci impostare il totale mostrato nel test, usa `--set-xp 100277`. Lo script rifiuta valori fuori dall'intervallo intero supportato dal formato e mostra nel riepilogo gli XP attuali e quelli risultanti.

5. Lo script crea una copia di sicurezza accanto a ogni file, con estensione `.bak` (se esiste già, usa un nome con data e ora). Avvia il gioco e controlla la schermata *Chapter Select*.
6. Se i progressi risultano azzerati o incoerenti, chiudi subito il gioco e ripristina la copia `.bak` prima di riavviarlo. Non lasciare che un salvataggio errato venga sincronizzato.

## Cosa è stato osservato nel confronto

- Salvataggio prima di una partita Facile: 827 byte, versione 5, 130 record di ricompensa, 100104 XP.
- Dopo aver completato un segmento Facile: stessa dimensione e stesso numero di ricompense; XP a 100277; un byte indicatore è passato da `01` a `04`.
- Il resto del file di progressione non è cambiato in quel confronto. Il file `GameStore` è rimasto invariato.
- Dopo aver impostato a `04` tutti e 16 i byte degli indicatori e riaperto il gioco, la schermata mostrava tutti gli indicatori dorati e gli XP erano ancora 100277.

Questi numeri documentano quella singola prova; lo script calcola gli offset dai dati presenti nel file e rifiuta dimensioni/versioni non riconosciute.

## File inclusi

- `INIZIA-QUI.txt` — istruzioni rapide in italiano.
- `unlock_story.py` — lettura preliminare e modifica con backup.
- `.gitignore` — esclude i salvataggi e le copie di sicurezza dalla repository.

Non caricare mai in questa repository i tuoi file di salvataggio, screenshot con il nome del profilo, SteamID o altri dati dell'account.
