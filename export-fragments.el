;;; export-fragments.el --- Export Org notes to body-only HTML fragments -*- lexical-binding: t; -*-

;;; Commentary:
;; Export Org notes to body-only HTML fragments.
;;
;; Default contract:
;;
;;   notes/foo.org
;;     -> build/foo.html
;;
;;   notes/project/bar.org
;;     -> build/project/bar.html
;;
;; This mirrors the note path so the Python builder can later wrap the
;; fragments into public pages without guessing.
;;
;; Normal usage from a running Emacs server:
;;
;;   emacsclient --eval '(progn
;;     (load-file "/path/to/export-fragments.el")
;;     (my/site-export-all-fragments))'
;;
;; Batch fallback:
;;
;;   emacs --batch --no-site-file -l export-fragments.el \
;;     --eval '(my/site-export-all-fragments)'

;;; Code:

(require 'cl-lib)
(require 'seq)
(require 'subr-x)

(defvar my/site-root nil
  "Root directory of the notes website project.")
(setq my/site-root
      (file-name-directory (or load-file-name default-directory)))

(defvar my/site-config-file nil
  "YAML configuration file for the notes website project.")
(setq my/site-config-file
      (expand-file-name "site.yml" my/site-root))

(defun my/site--trim-config-value (value)
  "Trim whitespace and simple quotes from VALUE read from `my/site-config-file`."
  (let ((trimmed (string-trim value)))
    (if (and (>= (length trimmed) 2)
             (or (and (string-prefix-p "\"" trimmed)
                      (string-suffix-p "\"" trimmed))
                 (and (string-prefix-p "'" trimmed)
                      (string-suffix-p "'" trimmed))))
        (substring trimmed 1 -1)
      trimmed)))

(defun my/site-config-value (section key fallback)
  "Return simple YAML value for SECTION.KEY, or FALLBACK if missing.

This intentionally supports only the small subset of YAML needed by
`site.yml`: top-level sections and two-space-indented scalar keys."
  (let ((current-section nil)
        (found nil))
    (when (file-readable-p my/site-config-file)
      (with-temp-buffer
        (insert-file-contents my/site-config-file)
        (goto-char (point-min))
        (while (and (not found) (not (eobp)))
          (let ((line (buffer-substring-no-properties
                       (line-beginning-position)
                       (line-end-position))))
            (cond
             ((string-match "\\`\\([[:alnum:]_-]+\\):[[:space:]]*\\'" line)
              (setq current-section (match-string 1 line)))
             ((and (equal current-section section)
                   (string-match
                    (format "\\`[[:space:]]\\{2\\}%s:[[:space:]]*\\(.*\\)\\'"
                            (regexp-quote key))
                    line))
              (setq found
                    (my/site--trim-config-value (match-string 1 line))))))
          (forward-line 1))))
    (if (and found (not (string-empty-p found))) found fallback)))

(defvar my/site-notes-dir nil
  "Directory containing source Org notes.")
(setq my/site-notes-dir
      (file-name-as-directory
       (expand-file-name (my/site-config-value "notes" "root" "notes") my/site-root)))

(defvar my/site-fragments-dir nil
  "Directory where exported HTML fragments are written.")
(setq my/site-fragments-dir
      (file-name-as-directory
       (expand-file-name
        (my/site-config-value "fragments" "root" "build")
        my/site-root)))

(defvar my/site-doom-root
  (expand-file-name "~/.config/doom_emacs/")
  "Path to the Doom Emacs installation whose packages should be reused in batch mode.")

(defun my/site--existing-directories (paths)
  "Return only existing directories from PATHS."
  (seq-filter #'file-directory-p paths))

(defun my/site--doom-build-roots ()
  "Return candidate straight build roots inside Doom."
  (let* ((straight-dir (expand-file-name ".local/straight/" my/site-doom-root))
         (candidates
          (append
           (file-expand-wildcards (expand-file-name "build-*" straight-dir))
           (file-expand-wildcards (expand-file-name "build/*" straight-dir))
           (file-expand-wildcards (expand-file-name "build" straight-dir)))))
    (my/site--existing-directories candidates)))

(defun my/site--doom-build-subdirs ()
  "Return all immediate package directories under Doom's build roots."
  (cl-loop for root in (my/site--doom-build-roots)
           append
           (cl-loop for f in (directory-files root t "^[^.]" t)
                    when (file-directory-p f)
                    collect f)))

(defun my/site-add-doom-packages-to-load-path ()
  "Add Doom's built package directories to `load-path`.

This is only needed for plain batch Emacs.  In an interactive Doom
session, packages should already be visible."
  (dolist (dir (my/site--doom-build-subdirs))
    (add-to-list 'load-path dir)))

(defun my/site-require-export-deps ()
  "Load Org export dependencies."
  ;; In an interactive Emacs server, these may already be available.
  ;; In batch Emacs, Doom has not populated `load-path`, so try Doom's
  ;; straight build dirs if htmlize is missing.
  (unless (require 'htmlize nil t)
    (my/site-add-doom-packages-to-load-path)
    (unless (require 'htmlize nil t)
      (error
       (concat
        "Could not load htmlize.\n\n"
        "Looked in current `load-path` and Doom build dirs under:\n"
        "  " my/site-doom-root "\n\n"
        "If using Doom, ensure htmlize is installed and run doom sync."))))

  (require 'org)
  (require 'ox-html))

(my/site-require-export-deps)

(setq org-export-use-babel nil
      org-src-fontify-natively t
      org-html-htmlize-output-type 'css
      org-html-head-include-default-style nil
      org-html-head-include-scripts nil
      org-html-preamble nil
      org-html-postamble nil
      org-html-use-infojs nil)

;; Distinguish =code= from ~verbatim~ in exported HTML.
(setq org-html-text-markup-alist
      '((bold . "<strong>%s</strong>")
        (code . "<code class=\"org-code\">%s</code>")
        (italic . "<em>%s</em>")
        (strike-through . "<del>%s</del>")
        (underline . "<span class=\"underline\">%s</span>")
        (verbatim . "<code class=\"org-verbatim\">%s</code>")))

(defun my/site--ignored-org-file-p (file)
  "Return non-nil if FILE should not be exported."
  (let ((name (file-name-nondirectory file)))
    (or (string-prefix-p ".#" name)
        (string-suffix-p "~" name)
        (string-prefix-p "#" name)
        (string-suffix-p "#" name))))

(defun my/site-org-note-files ()
  "Return all Org note files under `my/site-notes-dir`, recursively."
  (unless (file-directory-p my/site-notes-dir)
    (error "Notes directory does not exist: %s" my/site-notes-dir))
  (seq-filter
   (lambda (file)
     (and (file-regular-p file)
          (not (my/site--ignored-org-file-p file))))
   (directory-files-recursively my/site-notes-dir "\\.org\\'")))

(defun my/site-relative-note-path (org-file)
  "Return ORG-FILE path relative to `my/site-notes-dir`.

Example:
  project/foo.org"
  (file-relative-name org-file my/site-notes-dir))

(defun my/site-output-file-for-note (org-file)
  "Return mirrored HTML fragment path for ORG-FILE.

Example:
  notes/project/foo.org
    -> build/project/foo.html"
  (let* ((rel (my/site-relative-note-path org-file))
         (rel-html (concat (file-name-sans-extension rel) ".html")))
    (expand-file-name rel-html my/site-fragments-dir)))

(defun my/site-export-one-fragment (org-file)
  "Export ORG-FILE to a mirrored body-only HTML fragment."
  (let ((out-file (my/site-output-file-for-note org-file)))
    (make-directory (file-name-directory out-file) t)
    (message "Exporting %s -> %s" org-file out-file)
    (with-current-buffer (find-file-noselect org-file)
      (let ((org-export-body-only t))
        (org-export-to-file
            'html
            out-file
          nil     ; async
          nil     ; subtreep
          nil     ; visible-only
          t       ; body-only
          '(:with-toc nil))))))

(defun my/site-export-all-fragments ()
  "Export all Org notes to body-only HTML fragments."
  (interactive)
  (let ((files (my/site-org-note-files)))
    (unless files
      (error "No Org notes found in %s" my/site-notes-dir))
    (make-directory my/site-fragments-dir t)
    (dolist (org-file files)
      (my/site-export-one-fragment org-file))
    (message "Finished exporting %d Org fragment(s)." (length files))
    (length files)))

;;; export-fragments.el ends here
