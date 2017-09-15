#!/usr/bin/python

"""
Convert a notes-mode file to pdf (via latex, etc.)

@todo: support for \epsfig
"""

"""
Character codes:
  \0 = backslash
  \1 = open brace
  \2 = close brace
  \3 = \_
"""

import sys, re, os, shutil, os.path

# Latex header.
HEADER = r"""
\documentclass{article}
\usepackage{fullpage}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{alltt}
\usepackage{epsfig}
\usepackage[dvips, pagebackref, colorlinks=true,
            pdftitle={%s},
            pdfauthor={%s},
            bookmarks=true, bookmarksopen=false,
            pdfpagemode=UseOutlines]{hyperref}

\setlength{\parskip}{1ex}
\setlength{\parindent}{0ex}
\setlength{\topsep}{0.3em}
\setlength{\partopsep}{0em}

%% This is used to reduce spacing in bulleted lists.
\def\nogap{
    \setlength{\itemsep}{0em}
    \setlength{\parskip}{0em}}

%% Declare some symbols that x-emacs believes exists.
\DeclareTextSymbol{\textbackslash}{T1}{92}
\newcommand{\nsubset}{\not\subset}
\renewcommand{\textflorin}{\textit{f}}
\newcommand{\setB}{{\mathord{\mathbb B}}}
\newcommand{\setC}{{\mathord{\mathbb C}}}
\newcommand{\setN}{{\mathord{\mathbb N}}}
\newcommand{\setQ}{{\mathord{\mathbb Q}}}
\newcommand{\setR}{{\mathord{\mathbb R}}}
\newcommand{\setZ}{{\mathord{\mathbb Z}}}
\newcommand{\coloncolon}{\mathrel{::}}
\newcommand{\lsemantics}{\mathopen{\lbrack\mkern-3mu\lbrack}}
\newcommand{\rsemantics}{\mathclose{\rbrack\mkern-3mu\rbrack}}
\newcommand{\lcata}{\mathopen{(\mkern-3mu\mid}}
\newcommand{\rcata}{\mathopen{\mid\mkern-3mu)}}

\begin{document}
"""

FOOTER = r"""
\end{document}
"""

DEBUG=0

def dolists(notes):
    """
    Convert notes-style lists to LaTeX enum/itemize lists.
    """
    _BULLET_RE = re.compile(r'^([ \t]*)([*]|[-]|\d+\.)(.*)', re.MULTILINE)

    indent = [-1]
    bullets = []
    out = ''
    verbatim = 0
    for line in notes.split('\n'):
        # Skip verbatim areas..
        if re.search(r'\\begin{alltt}', line): verbatim = 1
        if re.search(r'\\end{alltt}', line): verbatim = 0
        if verbatim:
            out += line + '\n'
            continue

        m = _BULLET_RE.match(line)
        if m:
            spaces = len(m.group(1).replace('\t', '        '))
            bullet = m.group(2)

            # Start a new (sub)list.
            if spaces > indent[-1]:
                if bullet in ('*', '-'):
                    bullets.append('itemize')
                else:
                    bullets.append('enumerate')
                out += '\n\\vspace{-1ex}\\begin{%s}\\nogap\n' % bullets[-1]
                indent.append(spaces)

            # End one or more sublists.
            while spaces < indent[-1]:
                out += '\\vspace{-1ex}\\end{%s}\n\n' % bullets.pop()
                indent.pop()

            # List item.
            out += (' '*spaces) + '\\item{}' + m.group(3) + '\n'

        else:
            # End the last sublist..
            m = re.match('([ \t]*)', line)
            spaces = len(m.group(1).replace('\t', '        '))
            # End one or more sublists.
            while spaces <= indent[-1]:
                out += '\\vspace{-1ex}\\end{%s}\n\n' % bullets.pop()
                indent.pop()

            out += line + '\n'

    return out

def do_timestamps(notes):
    """
    Convert notes-style timestamps to headings.  I put a timestamp at
    the beginning of each day's class, so this puts each day on its
    own page.  The timestamp can optionally be followed (on the same
    line) by a title for that day's lecture.
    """
    import time
    _TIMESTAMP_RE = re.compile(r'^\[(\d\d/\d\d/\d\d) \d\d:\d\d [AP]M\](.*)$')
    just_did_timestamp = 0
    out = ''
    for line in notes.split('\n'):
        m = _TIMESTAMP_RE.match(line)
        if m is None:
            if just_did_timestamp and line.strip() != '':
                just_did_timestamp = 0
                if not re.match(r'>>?>?\s', line):
                    out += '\\vspace{2em}\n'
            out += line+'\n'
            continue

        (date,text) = m.groups()
        datestr = time.strftime('%A, %B %e, %Y',
                                time.strptime(date, '%m/%d/%y'))
        out += '\\newpage\n'
        if text:
            out += '\\begin{centering}\\LARGE %s\\\\' % text
            out += '\\end{centering}\\vspace{4mm}\n'
        out += '\\hrule\\hrule\\hrule\n'
        out += '\\begin{raggedleft}\\Large \\it \\hfill %s' % datestr
        out += '\\\\ \\end{raggedleft}\n\n\n'
        just_did_timestamp = 1
    return out

_VERB1_RE_A = re.compile(r'((\n[#]([ \t][^\n]*)?)+)', re.MULTILINE)
_VERB2_RE_A = re.compile(r'((\n[%]([ \t][^\n]*)?)+)', re.MULTILINE)
_VERB3_RE_A = re.compile(r'((\n[!]([ \t][^\n]*)?)+)', re.MULTILINE)
_VERB4_RE_A = re.compile(r'((\n[*]([ \t][^\n]*)?)+)', re.MULTILINE)
_VERB1_SUB_A = r"""

\\begin{tabular}{||l}
\\begin{minipage}{0.9\\textwidth}
\\begin{alltt}\\small\1
\\end{alltt}
\\end{minipage}
\\end{tabular}

"""
_VERB2_SUB_A = _VERB3_SUB_A = r"""

\\begin{tabular}{|l}
\\begin{minipage}{0.9\\textwidth}
\\begin{alltt}\\rmfamily\1
\\end{alltt}
\\end{minipage}
\\end{tabular}

"""
_VERB4_SUB_A = r"""

\\begin{tabular}{|l|}
\hline
\\begin{minipage}{0.9\\textwidth}
\\begin{alltt}\\bfseries\\rmfamily\\itshape\\large\1
\\end{alltt}
\\end{minipage}\\\\
\hline
\\end{tabular}

"""

# Subscript or superscript.  \1=open brace, \2=close brace.
_SCRIPT = r'(%s|%s|%s)' % ((r'%s[^%s]+%s' % ('\1','\1\2','\2')),
                           '\0[a-zA-Z0-9]+', r'[^{}_^\\]')

_FIGURE_RE = re.compile('^::FIGURE::(\d+)::FIGURE::$', re.MULTILINE)
_FIGURE_SUB = r"""\\end{alltt}
\\epsfig{file=figure\1.eps}
\\begin{alltt}"""

def notes2latex(notes, **headervars):
    """
    Convert a notes file to a LaTeX file.

    @type notes: C{string}
    """
    # Change backslashes to \0s, so we can tell our backslashes from theirs.
    notes = re.sub(r'\\', '\0', notes)
    notes = re.sub(r'\{', '\1', notes)
    notes = re.sub(r'\}', '\2', notes)
    notes = re.sub('\0_', '\3', notes)

    #notes = re.sub('\0epsfig\1([^\2]*file=)([^\2]+)\2',
    #               r'\\epsfig{\1%s/\2}' % os.curdir, notes)

    # In the case of expressions like {\'o} (for o with an accent), we
    # want to keep the {, }, and \ characters; change them back, to
    # prevent them from being rendered literally.
    notes = re.sub("\1\0(['\"c`]? ?\w)\2", r'{\\\1}', notes)

    # Timestamps.
    notes = do_timestamps(notes)

    # Headings.
    H1_RE = re.compile(r'^> (.*)$', re.MULTILINE)
    notes = H1_RE.sub('\n'+r'\\section{\1}'+'\n', notes)
    H2_RE = re.compile(r'^>> (.*)$', re.MULTILINE)
    notes = H2_RE.sub('\n'+r'\\subsection{\1}'+'\n', notes)
    H3_RE = re.compile(r'^>>> (.*)$', re.MULTILINE)
    notes = H3_RE.sub('\n'+r'\\subsubsection*{\1}'+'\n', notes)

    # Emphasis.
    notes = re.sub(r'!!(.*)!!', r" \\emph{\1} ", notes)

    # Some characters need to be in math mode.
    # (do this before verb, since verb introduces |'s)
    notes = re.sub(r'([<>|])', r'\\(\1\\)', notes)

    notes = _VERB1_RE_A.sub(_VERB1_SUB_A, notes)
    notes = _VERB2_RE_A.sub(_VERB2_SUB_A, notes)
    notes = _VERB3_RE_A.sub(_VERB3_SUB_A, notes)
    notes = _VERB4_RE_A.sub(_VERB4_SUB_A, notes)

    # Get rid of the verbatim markers.
    VERB_RE_B = re.compile(r'^[#%!*][ \t]?', re.MULTILINE)
    notes = VERB_RE_B.sub('', notes)

    # Handle sub & super scripts.  Run these regexps repeatedly, since
    # sub & superscripts might be nested.
    MATH_RE_A = re.compile(r'\^(%s)' % _SCRIPT)
    MATH_RE_B = re.compile(r'_(%s)' % _SCRIPT)
    while 1:
        notes2 = notes

        # Replace _ and ^ with \sb and \sp
        notes2 = MATH_RE_A.sub(r"\\(\\sp{\\text{\1}}\\)", notes2)
        notes2 = MATH_RE_B.sub(r"\\(\\sb{\\text{\1}}\\)", notes2)

        # Get rid of excess { and }s
        notes2 = re.sub("\\\\text{\1([^\1\2{}]*)\2}",
                        r'\\text{\1}', notes2)

        if notes2 == notes: break
        else: notes = notes2

    # Put appropriate elements in math mode.
    notes = re.sub('\0([a-zA-Z0-9]+)', r"\\(\\\1\\)", notes)

    # Get rid of any remaining ^s and _s (from nested use)
    notes = re.sub(r'\^', r'\\textasciicircum', notes)
    notes = re.sub(r'_', r'\\_', notes)

    # Some characters need to be backslashed
    notes = re.sub('([#$&%])', r'\\\1', notes)

    # Some commands are *not* supposed to be in math mode.
    notes = re.sub((r'(\\text(?!width)[a-zA-Z0-9]+|'+
                    r'\\l(?!\w)|\\o(?!\w))'),
                   r'\\textrm{\1}', notes)

    # Is this necessary?
    notes = re.sub('~', r'{\\textasciitilde}', notes)

    # If they backslashed braces, then unbackslash them.
    notes = re.sub('\0\1', '\1', notes)
    notes = re.sub('\0\2', '\2', notes)

    # Change any remaining backslashes to textbackslash, etc.
    notes = re.sub('\0', r'{\\textbackslash}', notes)
    notes = re.sub('\1', r'\\{', notes)
    notes = re.sub('\2', r'\\}', notes)
    notes = re.sub('\3', r'\\_', notes)

    # Handle figures
    notes = _FIGURE_RE.sub(_FIGURE_SUB, notes)
    notes = re.sub(r'\\begin{alltt}\n\\end{alltt}\n', '', notes)

    # Handle lists.
    notes = dolists(notes)

    # Get rid of 2 consecutive blank lines..
    notes = re.sub(r'\n([ \t]*\n)+', '\n\n', notes)

    # Fill in header variables.
    author = headervars.get('author', 'Edward Loper')
    title = headervars.get('title', '')
    header = HEADER % (author, title)

    return header+notes+FOOTER


def tree2ps(tree_str, outfile):
    # Use square braces.
    tree_str = re.sub(r'\[', '(', tree_str)
    tree_str = re.sub(r'\]', ')', tree_str)

    # Undo some of our earlier changes.. :-/
    tree_str = tree_str.strip()
    tree_str = re.sub(r'\\_', '_', tree_str)

# THE TREE2IMAGE VERSION:
    import tree2image
    tree = tree2image.parse_treebank_tree(tree_str, '()', 1)
    tree2image.tree2ps(outfile, tree, ('times', 9))

# THE NLTK VERSION:
#    from nltk.tree import parse_treebank
#    import nltk.draw.tree
#    # Hack to make tree sizes more reasonable:
#    nltk.draw.tree.TreeView._Y_SPACING = 8
#    nltk.draw.tree.TreeView._X_SPACING = 4
#
#    tree = parse_treebank(tree_str)
#    nltk.draw.tree.print_tree(tree, outfile, 8)

_FIGURE_NUMBER = 0
def do_figures(str, dir, type, show_original=None):
    if type == 'trees': braces = '[]'
    elif type == 'graphs': braces = '{}'
    elif type == 'plots': braces = ';;' # (no braces; plots are 1-line)
    else: raise ValueError('bad type')

    # By default, show originals for trees but not graphs or plots.
    if show_original is None:
        show_original = (type == 'trees')

    brace_count = 0
    fig = ''
    out = ''

    verbatim = 0
    sys.stdout.write('Converting %s' %type)
    for line in str.split('\n'):

        # Skip non-verbatim areas..
        if line[:2] != '# ':
            out += line + '\n'
            brace_count = 0
            fig = ''
            continue

        stripline = line[2:].strip()

        if (fig or (type == 'trees' and stripline[:1] == braces[0]) or
            (type == 'graphs' and stripline[:8] == 'digraph ') or
            (type == 'plots' and stripline[:5] == 'plot ' and
             stripline[-1] == ';')):
            fig += stripline + '\n'
            if show_original:
                out += line + '\n'
        else:
            out += line + '\n'

        if fig:
            brace_count += (stripline.count(braces[0]) -
                            stripline.count(braces[1]))
            if brace_count == 0 and stripline[-1:] == braces[1]:
                sys.stdout.write('.'); sys.stdout.flush()
                # We have a figure!
                global _FIGURE_NUMBER
                _FIGURE_NUMBER += 1
                epsname = 'figure%d.eps' % _FIGURE_NUMBER
                if type == 'trees':
                    try: tree2ps(fig, epsname)
                    except: print 'BAD TREE:\n'+fig; continue
                elif type == 'graphs':
                    figname = 'figure%d.fig' % _FIGURE_NUMBER
                    figfile = open(os.path.join(dir, figname), 'w')
                    figfile.write(fig)
                    figfile.close()
                    if os.system('dot %s -Tps -o %s' %
                                 (figname, epsname)) != 0:
                        print 'BAD DOT GRAPH:\n'+fig; continue
                elif type == 'plots':
                    if os.system("echo 'set term postscript eps;"+
                                 " set size 0.5,0.5;"+
                                 (' set output "%s";' % epsname) +
                                 fig + "' |gnuplot") != 0:
                        print 'BAD PLOT: %s\n' + fig; continue
                else:
                    assert 0, 'Bad type'
                out += '# ::FIGURE::%d::FIGURE::\n' % _FIGURE_NUMBER
                brace_count = 0
                fig = ''
    print
    return out

def latex2pdf(notes_str, outfile, trees=0, graphs=0, plots=0):
    olddir = os.path.abspath('.')

    # Make a temp directory
    tempdir = os.tempnam()
    while os.path.exists(tempdir): tempdir = os.tempnam()

    try:
        os.mkdir(tempdir)
        os.chdir(tempdir)

        # Special handling: figures.  Do this *before* we do other
        # latex conversions, because the text within the figure should
        # be literal..
        if trees:
            notes_str = do_figures(notes_str, tempdir, 'trees')
        if graphs:
            notes_str = do_figures(notes_str, tempdir, 'graphs')
        if plots:
            notes_str = do_figures(notes_str, tempdir, 'plots')

        # Convert the notes file to latex.
        latex_str = notes2latex(notes_str, title=outfile.replace('.pdf',''))

        # Write the latex file
        texfile = open("file.tex", 'w')
        texfile.write(latex_str)
        texfile.close()

        # Run latex twice (for bookmarks & x-refs)
        command = 'latex file.tex'
        print command
        if os.system(command) != 0:
            os.system('less file.tex')
            raise ValueError('Warning: latex failed')
        command = 'latex file.tex >/dev/null'
        print command
        if os.system(command) != 0:
            os.system('less file.tex')
            raise ValueError('Warning: latex failed')

        if DEBUG:
            os.system('xdvi file.dvi')
            return

        # Run dvips
        command = 'dvips -q file.dvi -o file.ps -G0 -Ppdf'
        print command
        if os.system(command) != 0:
            raise ValueError('Warning: dvips failed')
        os.system('cp file.ps /tmp/genomics.ps')

        # Run ps2pdf
        command = ('ps2pdf -sPAPERSIZE=letter -dMaxSubsetPct=100 '+
                   '-dCompatibilityLevel=1.2 -dSubsetFonts=true '+
                   '-dEmbedAllFonts=true file.ps file.pdf')
        print command
        if os.system(command) != 0:
            raise ValueError('Warning: ps2pdf failed')

        # Read the pdf
        pdffile = open("file.pdf", 'r')
        pdf_str = pdffile.read()
        pdffile.close()

        # Write the output.
        os.chdir(olddir)
        outfile = open(outfile, 'w')
        outfile.write(pdf_str)
        outfile.close()

    finally:
        os.chdir(olddir)
        shutil.rmtree(tempdir)

def usage():
    print "usage: parsenotes [-trees] file.notes"
    #sys.exit(-1)

def main():
    trees = graphs = plots = 0
    infile = None
    for arg in sys.argv[1:]:
        if arg[:1] == '-':
            if arg in ('-trees', '-tree'): trees = 1
            elif arg in ('-graphs', '-graph'): graphs = 1
            elif arg in ('-plots', '-plot'): plots = 1
            else:
                return usage()
        else:
            if infile is None: infile = arg
            else: return usage()
    if infile is None: return usage()

    outfile = re.sub('.notes$', '.pdf', infile)
    if infile == outfile:
        print 'Expected a notes file'

    notes = '\n'+open(infile, 'r').read()+'\n'
    print '%s --> %s' % (infile, outfile)
    latex2pdf(notes, outfile, trees, graphs, plots)

if __name__ == '__main__': main()
