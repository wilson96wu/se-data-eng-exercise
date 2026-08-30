# `source` command usage cheatsheet

`source` (alias: `.`) is a shell builtin that runs a script in the **current shell session** instead of a subshell — so any variables, functions, or environment changes it makes persist after it finishes. This is why it's used for anything that needs to affect your current shell.

## Syntax
```bash
source <file> [arguments]
. <file> [arguments]        # POSIX-compatible alias, works in bash/zsh/sh
```

## Common usages

### 1. Activate a Python virtual environment
```bash
source venv/bin/activate
source airflow/.venv/bin/activate
```
Sets `VIRTUAL_ENV`, prepends the venv's `bin/` to `PATH`, and updates your prompt.

### 2. Reload shell config after editing it
```bash
source ~/.zshrc      # zsh
source ~/.bashrc      # bash
source ~/.bash_profile
```
Applies changes (aliases, exports, functions) without opening a new terminal.

### 3. Load environment variables from a file
```bash
source .env
```
Common in projects using a plain `KEY=value` `.env` file (note: this only works if the file is valid shell syntax, not raw YAML/JSON).

### 4. Run a script that must modify the current shell
```bash
source setup.sh
```
Useful when a script needs to `cd`, `export`, or define functions that should remain active after the script ends — running it normally (`./setup.sh`) would only affect a child process and changes would be lost.

### 5. Deactivate a virtual environment
```bash
deactivate
```
(Not `source`-based itself, but `activate` defines this function via `source`, which is why it only exists after sourcing.)

### 6. Source conditionally / with arguments
```bash
[ -f ~/.env.local ] && source ~/.env.local
source myscript.sh arg1 arg2   # $1, $2 available inside the script
```

## Key distinction: `source script.sh` vs `./script.sh`
| | `source script.sh` | `./script.sh` |
|---|---|---|
| Runs in | current shell | new subshell/process |
| Variable/env changes persist after? | Yes | No |
| Needs execute permission (`chmod +x`)? | No | Yes |
| Needs shebang line? | No | Yes |

## Checking it worked
```bash
echo $VIRTUAL_ENV      # after sourcing a venv activate script
type source             # confirms it's a shell builtin
```
