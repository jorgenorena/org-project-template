output := `python -c 'import yaml; print(yaml.safe_load(open("site.yml"))["site"]["output"])'`
fragments := `python -c 'import yaml; print(yaml.safe_load(open("site.yml"))["fragments"]["root"])'`

default:
    just --list

fragments:
    emacsclient --eval '(progn (load-file "{{justfile_directory()}}/export-fragments.el") (my/site-export-all-fragments))'

build:
    python build_site.py

quick: fragments build

serve:
    python -m http.server 8000 --directory {{ output }}

site: quick serve

clean:
    rm -rf {{ fragments }} {{ output }} __pycache__
