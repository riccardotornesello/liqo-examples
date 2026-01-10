# Sistema di Logging Testbench-v2

Il sistema di logging di testbench-v2 fornisce un modo strutturato per visualizzare i progressi delle operazioni con supporto per passaggi e sotto-passaggi gerarchici.

## Caratteristiche

- ✅ **Visualizzazione chiara dello stato**: Icone intuitive per ogni stato (✅ completato, ℹ️ in corso, ❌ fallito, ⏳ in attesa)
- 🔄 **Passaggi gerarchici**: Supporto per sotto-passaggi con indentazione automatica
- 🎯 **Context manager**: Gestione automatica dello stato dei passaggi
- 📊 **Aggiornamento dinamico**: Possibilità di aggiornare lo stato dei passaggi in tempo reale

## Utilizzo Base

### Creazione di un logger

```python
from logging import StepLogger

logger = StepLogger()
```

### Passaggi semplici

```python
# Aggiungere e completare un passaggio
step = logger.add_step("Cluster A creato")
logger.complete_step(step)

# Visualizzare i passaggi
logger.display()
```

Output:
```
✅ Cluster A creato
```

### Passaggi con sotto-passaggi

```python
# Creare un passaggio principale
step = logger.add_step("Creazione cluster B in corso")
logger.start_step(step)

# Aggiungere sotto-passaggi
sub1 = step.add_substep("Configurazione iniziale completata")
logger.complete_step(sub1)

sub2 = step.add_substep("CNI installata")
logger.complete_step(sub2)

sub3 = step.add_substep("Creazione risorse demo")
logger.start_step(sub3)

logger.display()
```

Output:
```
ℹ️ Creazione cluster B in corso...
  - ✅ Configurazione iniziale completata
  - ✅ CNI installata
  - ℹ️ Creazione risorse demo...
```

## Utilizzo Avanzato

### Context Manager

Il modo più semplice per gestire automaticamente lo stato dei passaggi:

```python
logger = StepLogger()

# Passaggio singolo con context manager
with logger.step("Inizializzazione ambiente"):
    # Il passaggio è automaticamente marcato come "in corso"
    # Esegui operazioni...
    pass
    # Il passaggio è automaticamente marcato come "completato"

# Passaggio con sotto-passaggi
with logger.step("Setup cluster principale") as step:
    with logger.substep(step, "Creazione nodi"):
        # Operazioni...
        pass
    
    with logger.substep(step, "Configurazione rete"):
        # Operazioni...
        pass

logger.display()
```

### Gestione degli errori

I context manager gestiscono automaticamente gli errori:

```python
logger = StepLogger()

try:
    with logger.step("Operazione rischiosa"):
        # Se viene sollevata un'eccezione, il passaggio è marcato come fallito
        raise Exception("Errore!")
except Exception:
    pass

logger.display()
```

Output:
```
❌ Operazione rischiosa
```

## Stati dei passaggi

Ogni passaggio può avere uno dei seguenti stati:

- ⏳ **PENDING**: Passaggio non ancora iniziato
- ℹ️ **IN_PROGRESS**: Passaggio in corso (con "...")
- ✅ **COMPLETED**: Passaggio completato con successo
- ❌ **FAILED**: Passaggio fallito

## Metodi disponibili

### StepLogger

- `add_step(name: str) -> Step`: Aggiunge un nuovo passaggio principale
- `start_step(step: Step)`: Marca un passaggio come "in corso"
- `complete_step(step: Step)`: Marca un passaggio come "completato"
- `fail_step(step: Step)`: Marca un passaggio come "fallito"
- `display()`: Visualizza tutti i passaggi con il loro stato corrente
- `step(name: str)`: Context manager per passaggi automatici
- `substep(parent_step: Step, name: str)`: Context manager per sotto-passaggi automatici

### Step

- `add_substep(name: str) -> Step`: Aggiunge un sotto-passaggio
- `format_line() -> str`: Formatta il passaggio come stringa visualizzabile

## Esempi completi

Vedere il file `main.py` per esempi completi di utilizzo che dimostrano:
- Passaggi completati
- Passaggi in corso con sotto-passaggi
- Utilizzo dei context manager
- Stati misti (completato, fallito, in corso, in attesa)

## Integrazione nel codice esistente

Il nuovo sistema di logging è completamente compatibile con le funzioni di logging esistenti:

```python
from logging import log_info, log_success, log_warning, log_error, StepLogger

# Le vecchie funzioni continuano a funzionare
log_info("Messaggio informativo")
log_success("Operazione riuscita")

# Il nuovo sistema per passaggi strutturati
logger = StepLogger()
with logger.step("Operazione complessa"):
    log_info("Dettagli dell'operazione")
logger.display()
```
