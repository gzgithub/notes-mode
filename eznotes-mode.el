;; eznotes-mode.el -- an emacs mode for taking notes
;;
;; Notes mode is an Emacs mode for taking notes.  In particular, it
;; is intended for use taking notes during lectures, conferences, etc.
;; Notes mode does some syntactic highlighting, and uses x-render
;; mode.  Currently, it colorizes the following constructs:
;;   - Headings: lines starting with ">", ">>", or ">>>"
;;   - Timestamps of the form "[09/11/02 04:49 AM]"
;;   - Flagged regions of the form "!!...!!"
;;   - Lines beginning with "#", "*", "!", or "%" followed by
;;      whitespace ("marked" regions)
;;   - Unordered lists, which can use either "-" or "*" as a bullet
;;   - Ordered lists, which use "n." as a bullet (where n is a number)
;;
;; When taking notes, you may also want to use the x-render minor
;; mode, which lets you render graphs, plots, and syntax trees inline
;; in your notes.
;;
;; An accompanying program, parsenotes.py, will convert notes files to
;; pretty pdf files.  It uses the constructs marked in the notes file
;; to format the text.  In particular:
;;   - headings are rendered as headings
;;   - Timestamps start a new page (I enter a timestamp at the
;;      beginning of every lecture/session/etc), with the timestamp
;;      rendered as a heading at the top of the page.  If text follows
;;      the timestamp, on the same line, then it is added to the
;;      heading.
;;   - Flagged regions are rendered with emph
;;   - "#" marked regions are rendered as preformatted text, with a
;;     double-line on the left margin.
;;   - "%" and "!" marked regions are rendered with a single line on
;;      the left margin.
;;   - "*" marked regions are rendered in a box, in a larg bold italic
;;      font.
;; Additionally, parsenotes knows about x-render mode, and will
;; display graphs, plots, and syntax trees in the pdf file.

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Utility functions
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defun timestamp () (interactive)
  (shell-command "date '+[%m/%d/%y %I:%M %p]'" 't)
  (exchange-point-and-mark))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Font-lock keywords
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
(defconst notes-font-lock-keywords
  (let (
        ;; Always use these keywords:
        (basic-keywords
         '(
          ;; Timestamps
          ("\\(\\[../../.. [0-9][0-9]:[0-9][0-9] [PA]M\\]\\)"
           1 'notes-daytime-face)

          ;; Headings
          ("\\(^> .*\\)" 1 'notes-heading1-face)
          ("\\(^>> .*\\)" 1 'notes-heading2-face)
          ("\\(^>>> .*\\)" 1 'notes-heading3-face)

          ;; Important things
          ("\\(!!.*!!\\)" 1 'notes-important-face)

          ;; Marked regions
          ("\\(^#[ 	].*\\|^#$\\)" 1 'notes-marked1-face)
          ("\\(^%[ 	].*\\|^%$\\)" 1 'notes-marked2-face)
          ("\\(^![ 	].*\\|^!$\\)" 1 'notes-marked3-face)
          ("\\(^*[ 	].*\\|^*$\\)" 1 'notes-marked4-face)
          ("^[ 	]*\\([0123456789]*\\.\\)" 1 'notes-bullet-face)
          ("^[ 	]*\\(\\*\\)" 1 'notes-bullet-face)
          ("^[ 	]*\\(-\\)" 1 'notes-bullet-face)))

        ;; Only use these keywords if x-symbol mode is available:
        (x-symbol-keywords '()))
;         '(
;           ;; Hide "_" and "^" for sub/superscripts.
;           (x-symbol-tex-match-subscript
;            (1 x-symbol-invisible-face t)
;            (2 (if (eq (char-after (match-beginning 1)) ?\_)
;                   (quote x-symbol-sub-face) (quote x-symbol-sup-face))
;               prepend))
;           (x-symbol-tex-match-simple-subscript
;            (1 x-symbol-invisible-face t)
;            (2 (if (eq (char-after (match-beginning 1)) ?\_)
;                   (quote x-symbol-sub-face) (quote x-symbol-sup-face))
;               prepend)))))
    (if (or (featurep 'x-symbol) (featurep 'x-symbol-autoloads))
        (append basic-keywords x-symbol-keywords)
      basic-keywords)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Register the Mode
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Register the font-lock keywords (xemacs)
(put 'eznotes-mode 'font-lock-defaults '(notes-font-lock-keywords))

;; Register the font-lock keywords (gnu emacs)
(defvar font-lock-defaults-alist nil) ; in case we're in xemacs
(setq font-lock-defaults-alist
      (append font-lock-defaults-alist
              '((eznotes-mode notes-font-lock-keywords t nil nil nil))))

;; Register the fact that the notes mode uses x-symbol.
(if (or (featurep 'x-symbol) (featurep 'x-symbol-autoloads))
    (x-symbol-register-language 'tex 'x-symbol-tex '(eznotes-mode)))

;; Use notes mode for files ending in .notes
(setq auto-mode-alist (cons '("\\.notes\\'" . eznotes-mode)
                            auto-mode-alist))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Define Fonts
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(defface notes-bullet-face
  '((((class color) (background dark))
     (:foreground "#68f"))
    (t (:foreground "008")))
  "Face for bulleted list bullets in notes mode")

(defface notes-daytime-face
  '((t
     (:foreground "#3a9" :family "terminal")))
  "Face for daytime stamps in notes mode")

(defface notes-important-face
  '((((class color) (background dark))
     (:foreground "#f55"))
    (t
      (:foreground "#f00")))
  "Face for flagged text in notes mode")

(defface notes-heading1-face
  '((((class color) (background dark))
     (:foreground "#0ff" :weight bold :height 1.6 :family "lucida"))
    (t
      (:foreground "#066" :weight bold :height 1.6 :family "lucida")))
  "Face for level-1 headings in notes mode")

(defface notes-heading2-face
  '((((class color) (background dark))
     (:foreground "#5d8" :underline t :height 1.4 :family "lucida"))
    (t
      (:foreground "#2a2" :underline t :height 1.4 :family "lucida")))
  "Face for level-2 headings in notes mode")

(defface notes-heading3-face
  '((((class color) (background dark))
     (:foreground "#7bf" :height 1.3 :family "lucida"))
    (t
      (:foreground "#38a" :height 1.3 :family "lucida")))
  "Face for level-3 headings in notes mode")

(defface notes-marked1-face 
  '((((class color) (background dark))
     (:foreground "#dff" :family "lucidatypewriter"))
    (t
      (:foreground "#456" :family "lucidatypewriter")))
  "Face for #-marked regions in notes mode")

(defface notes-marked2-face 
  '((((class color) (background dark))
     (:foreground "#0f0" :family "lucidatypewriter"))
    (t
      (:foreground "#080" :family "lucidatypewriter")))
  "Face for %-marked regions in notes mode")

(defface notes-marked3-face 
  '((((class color) (background dark))
     (:foreground "#8cf" :family "lucidatypewriter"))
    (t
      (:foreground "#056" :family "lucidatypewriter")))
  "Face for !-marked regions in notes mode")

(defface notes-marked4-face 
  '((((class color) (background dark))
     (:foreground "#f80" :family "lucidatypewriter"))
    (t
      (:foreground "#840" :family "lucidatypewriter")))
  "Face for *-marked regions in notes mode")

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Notes Mode
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define-derived-mode eznotes-mode text-mode "Notes"
  "A mode for taking notes.  It uses font lock to mark the following
constructs:
  - Headings: lines starting with \">\", \">>\", or \">>>\"
  - Timestamps of the form \"[09/11/02 04:49 AM]\" (generated by
    ctrl-t).
  - Flagged regions of the form \"!!...!!\"
  - Lines beginning with \"#\", \"*\", \"!\", or \"%\" followed by
     whitespace (\"marked\" regions)
  - Unordered lists, which can use either \"-\" or \"*\" as a bullet
  - Ordered lists, which use \"n.\" as a bullet (where n is a number)

marked regions, timestamps, etc.  It uses x-symbol to render special
characters.

Key bindings:
\\{eznotes-mode-map}
"
  ;; Allow subscripts/superscripts with any face.
  (when (or (featurep 'x-symbol) (featurep 'x-symbol-autoloads))
    (setq x-symbol-subscripts 't)
    (setq x-symbol-tex-font-lock-allowed-faces 't))

  ;; Enable auto-fill mode.
  (auto-fill-mode 1)

  ;; Enable font-lock mode.
  (if (featurep 'font-lock) (font-lock-mode 1))
  )

(provide 'eznotes-mode)
;;; eznotes-mode ends here
