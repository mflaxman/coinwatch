# Neutrino Watch Only Wallet

# WARNING
This is a work-in-progress with known issues.

## Privacy Warning for Clients
Anyone who uses this service is inherently delegating some trust.
You should understand these tradeoffs when using a service like this.

#### Install
```
$ python3 main.py 
$ python3 -m pip install virtualenv && python3 -m virtualenv .venv3 &&  source .venv3/bin/activate
$ pip3 install -r requirements.txt 
```

## Run
```bash
$ CORE_USER=specter CORE_PASSWORD=supersecure CORE_HOST=youripordomain.com CORE_PORT=18332 PYTHON_HOST=localhost PYTHON_PORT=8080 python3 main.py
```
(only `CORE_USER` and `CORE_PASSWORD` environmental variables are strictly required, the rest have sensible defaults that may work for you)
