output := `python -c 'import yaml; print(yaml.safe_load(open("site.yml"))["site"]["output"])'`
fragments := `python -c 'import yaml; print(yaml.safe_load(open("site.yml"))["fragments"]["root"])'`
latex_output := `python -c 'import yaml; print(yaml.safe_load(open("site.yml"))["latex"]["root"])'`

default:
    just --list

fragments:
    emacsclient --eval '(progn (load-file "{{justfile_directory()}}/export-fragments.el") (my/site-export-all-fragments))'

tex-fragments:
    python export_tex.py fragments

build:
    python build_site.py

quick: fragments tex-fragments build

latex:
    emacsclient --eval '(progn (load-file "{{justfile_directory()}}/export-fragments.el") (my/site-export-all-latex))'
    python export_tex.py latex

serve port="8000":
    python serve_site.py {{ port }}

serve-static port="8000":
    python -m http.server {{ port }} --directory {{ output }}

site port="8000": quick
    python serve_site.py {{ port }}

clean:
    rm -rf {{ fragments }} {{ latex_output }} {{ output }} __pycache__
