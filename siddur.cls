\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{siddur}[2026/07/14 Custom class for reMarkable Paper Pro Siddur]

% Inherit from extarticle for the 14pt base font (acting mostly as a fallback now)
\LoadClass[14pt]{extarticle}

% Screen size mathematically derived from 1696x954 px @ 264 PPI
\RequirePackage[paperwidth=3.61in, paperheight=6.42in, margin=0.15in]{geometry}

% Languages and Typography
\RequirePackage{polyglossia}
\RequirePackage{fontspec}
\RequirePackage{xparse}

\setdefaultlanguage{english}
\setotherlanguage{hebrew}

% --- LATIN SERIF (English Translation & Commentary) ---
\setmainfont[
  Path=../fonts/skolar/,
  Extension=.otf,
  UprightFont=skolar_latin_regular,
  BoldFont=skolar_latin_bold,
  ItalicFont=skolar_latin_italic,
  BoldItalicFont=skolar_latin_bold_italic
]{Skolar}

% --- HEBREW SERIF (Liturgical Text) ---
% Pulling natively from Overleaf's system fonts, no Path required.
\newfontfamily\hebrewfont[
  Script=Hebrew,
  Scale=MatchUppercase % Keeps it mathematically balanced with the Latin text
]{Noto Serif Hebrew}

% --- LATIN CONDENSED (Optional: Transliterations or Headers) ---
\newfontfamily\condensedfont[
  Path=../fonts/skolar/,
  Extension=.otf,
  UprightFont=skolar_sans_latin_condensed_regular,
  BoldFont=skolar_sans_latin_condensed_bold,
  ItalicFont=skolar_sans_latin_condensed_italic,
  BoldItalicFont=skolar_sans_latin_condensed_bold_italic
]{Skolar Sans Condensed}

% ==========================================
% SEMANTIC TEXT STYLES (EXPLICIT PT/PC SIZING)
% ==========================================

% Note: 1pc = 12pt. 
% \fontsize{Point-Size}{Leading-Size}\selectfont

% 1. Heading 1 (Massive Hebrew Title)
\newcommand{\headingone}[1]{%
  \par\vspace{1pc}%
  {\centering\hebrewfont\fontsize{36pt}{40pt}\selectfont\texthebrew{#1}\par}%
  \vspace{0.5pc}%
}

% 2. Subheading (English Title)
\newcommand{\subheading}[1]{%
  \par\vspace{0.5pc}%
  {\centering\addfontfeatures{Letters=SmallCaps}\fontsize{14pt}{18pt}\selectfont #1\par}%
  \vspace{0.5pc}%
}

% 3. Heading Note (Instructional text)
\newcommand{\headingnote}[1]{%
  \par\vspace{0.5pc}%
  {\centering\itshape\fontsize{11pt}{14pt}\selectfont #1\par}%
  \vspace{1pc}%
}

% 4. Entry (E.g., Psalm citation)
\newcommand{\entry}[1]{%
  \par\vspace{0.5pc}%
  {\centering\condensedfont\fontsize{10pt}{12pt}\selectfont\MakeUppercase{#1}\par}%
  \vspace{1pc}%
}

% 5. Hebrew Liturgical Text (Standard block)
\newenvironment{hetext}
  {\par\vspace{1pc}\begingroup\raggedleft\begin{hebrew}\hebrewfont\fontsize{18pt}{22pt}\selectfont}
  {\end{hebrew}\par\endgroup\vspace{1pc}}

% 6. Transliteration (Standard block)
\newenvironment{translit}
  {\par\vspace{1pc}\begingroup\raggedright\fontsize{10pt}{14pt}\selectfont}
  {\par\endgroup\vspace{1pc}}

% 7. English Translation
\newenvironment{entext}
  {\par\vspace{1pc}\begingroup\raggedright\fontsize{12pt}{16pt}\selectfont}
  {\par\endgroup\vspace{1pc}}

% 8. Commentary Note
\newenvironment{note}
  {\par\vspace{1pc}\begingroup\noindent\fontsize{10pt}{13pt}\selectfont}
  {\par\endgroup\vspace{1pc}}

% ==========================================
% INTERLINEAR CHANT LOGIC
% ==========================================

% 9. Interlinear Chant Line
% \chantline{Hebrew text}[Optional transliteration]
\NewDocumentCommand{\chantline}{m o}{%
  {\hebrewfont\fontsize{18pt}{22pt}\selectfont #1}%
  \IfValueT{#2}{%
    \\*[-0.2pc]% Pulls the transliteration slightly closer to the Hebrew
    \textenglish{\condensedfont\fontsize{10pt}{12pt}\selectfont\MakeUppercase{#2}}%
  }%
  \\[0.5pc]% Space after the matched pair
}

% 10. Interlinear Chant Block
\newenvironment{chantblock}
  {\par\vspace{1pc}\begingroup\raggedleft\begin{hebrew}}
  {\end{hebrew}\par\endgroup\vspace{1pc}}

\endinput