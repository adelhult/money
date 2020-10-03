![logo](https://raw.githubusercontent.com/adelhult/money/master/static/logo/alternative192.png)
# money
A small, self-hosted web app for managing shared household expenses.

## Installation

1. Clone this repo
2. Install [flask](https://pypi.org/project/Flask/)
3. Set an env var so flask can know where the server is. `export FLASK_ENV="main"`
4. Create a file named `configuration.json` and insert the following rows:
```json
{
    "person_a": "<INSERT NAME>",
    "person_b": "<INSERT NAME>",
    "currency_long": "kronor",
    "currency_short": "kr",
    "database_name": "database_transactions"
}
```
5. Run `python3 -m run flask --host 0.0.0.0`


## TODO
* Clean-up, the code is currently pretty ugly
* Better UX
* Improve fault tolerance
* More data, total number of expenses etc.
