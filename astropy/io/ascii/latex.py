# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""An extensible ASCII table reader and writer.

latex.py:
  Classes to read and write LaTeX tables

:Copyright: Smithsonian Astrophysical Observatory (2011)
:Author: Tom Aldcroft (aldcroft@head.cfa.harvard.edu)
"""

##
## Redistribution and use in source and binary forms, with or without
## modification, are permitted provided that the following conditions are met:
##     * Redistributions of source code must retain the above copyright
##       notice, this list of conditions and the following disclaimer.
##     * Redistributions in binary form must reproduce the above copyright
##       notice, this list of conditions and the following disclaimer in the
##       documentation and/or other materials provided with the distribution.
##     * Neither the name of the Smithsonian Astrophysical Observatory nor the
##       names of its contributors may be used to endorse or promote products
##       derived from this software without specific prior written permission.
##
## THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
## ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
## WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
## DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
## DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
## (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
## LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
## ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
## (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
## SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import re
from . import core

latexdicts = {'AA':  {'tabletype': 'table',
                      'header_start': r'\hline \hline', 'header_end': r'\hline',
                      'data_end': r'\hline'},
              'doublelines': {'tabletype': 'table',
                              'header_start': r'\hline \hline', 'header_end': r'\hline\hline',
                              'data_end': r'\hline\hline'},
              'template': {'tabletype': 'tabletype', 'caption': 'caption',
                           'col_align': 'col_align', 'preamble': 'preamble',
                           'header_start': 'header_start',
                           'header_end': 'header_end', 'data_start': 'data_start',
                           'data_end': 'data_end', 'tablefoot': 'tablefoot',
                           'units': {'col1': 'unit of col1', 'col2': 'unit of col2'}}
              }


def add_dictval_to_list(adict, key, alist):
    '''add a value from a dictionary to a list

    :param adict: dictionary
    :param key: key of value
    :param list: list where value should be added
    '''
    if key in adict.keys():
        if isinstance(adict[key], basestring):
            alist.append(adict[key])
        else:
            alist.extend(adict[key])


def find_latex_line(lines, latex):
    '''Find the first line which matches a patters

    :param lines: list of strings
    :param latex: search pattern
    :returns: line number or None, if no match was found
    '''
    re_string = re.compile(latex.replace('\\', '\\\\'))
    for i, line in enumerate(lines):
        if re_string.match(line):
            return i
    else:
        return None


class LatexHeader(core.BaseHeader):
    header_start = r'\begin{tabular}'

    def start_line(self, lines):
        line = find_latex_line(lines, self.header_start)
        if line:
            return line + 1
        else:
            return None

    def write(self, lines):
        if not 'col_align' in self.latex.keys():
            self.latex['col_align'] = len(self.cols) * 'c'

        lines.append(r'\begin{' + self.latex['tabletype'] + r'}')
        add_dictval_to_list(self.latex, 'preamble', lines)
        if 'caption' in self.latex.keys():
            lines.append(r'\caption{' + self.latex['caption'] + '}')
        lines.append(self.header_start + r'{' + self.latex['col_align'] + r'}')
        add_dictval_to_list(self.latex, 'header_start', lines)
        lines.append(self.splitter.join([x.name for x in self.cols]))
        if 'units' in self.latex.keys():
            lines.append(self.splitter.join([self.latex['units'].get(x.name, ' ')
                                             for x in self.cols]))
        add_dictval_to_list(self.latex, 'header_end', lines)


class LatexData(core.BaseData):
    data_start = None
    data_end = r'\end{tabular}'

    def start_line(self, lines):
        if self.data_start:
            return find_latex_line(lines, self.data_start)
        else:
            return self.header.start_line(lines) + 1

    def end_line(self, lines):
        if self.data_end:
            return find_latex_line(lines, self.data_end)
        else:
            return None

    def write(self, lines):
        add_dictval_to_list(self.latex, 'data_start', lines)
        core.BaseData.write(self, lines)
        add_dictval_to_list(self.latex, 'data_end', lines)
        lines.append(self.data_end)
        add_dictval_to_list(self.latex, 'tablefoot', lines)
        lines.append(r'\end{' + self.latex['tabletype'] + '}')


class LatexSplitter(core.BaseSplitter):
    '''Split LaTeX table date. Default delimiter is `&`.
    '''
    delimiter = '&'

    def process_line(self, line):
        """Remove whitespace at the beginning or end of line. Also remove
        \\ at end of line"""
        line = line.split('%')[0]
        line = line.strip()
        if line[-2:] == r'\\':
            line = line.strip(r'\\')
        else:
            raise core.InconsistentTableError(r'Lines in LaTeX table have to end with \\')
        return line

    def process_val(self, val):
        """Remove whitespace and {} at the beginning or end of value."""
        val = val.strip()
        if val and (val[0] == '{') and (val[-1] == '}'):
            val = val[1:-1]
        return val

    def join(self, vals):
        '''Join values together and add a few extra spaces for readability'''
        delimiter = ' ' + self.delimiter + ' '
        return delimiter.join(x.strip() for x in vals) + r' \\'


class Latex(core.BaseReader):
    r'''Write and read LaTeX tables.

    This class implements some LaTeX specific commands.  Its main
    purpose is to write out a table in a form that LaTeX can compile. It
    is beyond the scope of this class to implement every possible LaTeX
    command, instead the focus is to generate a syntactically valid
    LaTeX tables.

    This class can also read simple LaTeX tables (one line per table
    row, no ``\multicolumn`` or similar constructs), specifically, it
    can read the tables that it writes.

    Reading a LaTeX table, the following keywords are accepted:

    **ignore_latex_commands** :
        Lines starting with these LaTeX commands will be treated as comments (i.e. ignored).

    When writing a LaTeX table, the some keywords can customize the
    format.  Care has to be taken here, because python interprets ``\\``
    in a string as an escape character.  In order to pass this to the
    output either format your strings as raw strings with the ``r``
    specifier or use a double ``\\\\``.

    Examples::

        caption = r'My table \label{mytable}'
        caption = 'My table \\\\label{mytable}'

    **latexdict** : Dictionary of extra parameters for the LaTeX output

        * tabletype : used for first and last line of table.
            The default is ``\\begin{table}``.  The following would generate a table,
            which spans the whole page in a two-column document::

                ascii.write(data, sys.stdout, Writer = ascii.Latex,
                            latexdict = {'tabletype': 'table*'})

        * col_align : Alignment of columns
            If not present all columns will be centered.

        * caption : Table caption (string or list of strings)
            This will appear above the table as it is the standard in
            many scientific publications.  If you prefer a caption below
            the table, just write the full LaTeX command as
            ``latexdict['tablefoot'] = r'\caption{My table}'``

        * preamble, header_start, header_end, data_start, data_end, tablefoot: Pure LaTeX
            Each one can be a string or a list of strings. These strings
            will be inserted into the table without any further
            processing. See the examples below.

        * units : dictionary of strings
            Keys in this dictionary should be names of columns. If
            present, a line in the LaTeX table directly below the column
            names is added, which contains the values of the
            dictionary. Example::

              from astropy.io import ascii
              data = {'name': ['bike', 'car'], 'mass': [75,1200], 'speed': [10, 130]}
              ascii.write(data, Writer=ascii.Latex,
                               latexdict = {'units': {'mass': 'kg', 'speed': 'km/h'}})

            If the column has no entry in the `units` dictionary, it defaults
            to `' '`.

        Run the following code to see where each element of the
        dictionary is inserted in the LaTeX table::

            from astropy.io import ascii
            data = {'cola': [1,2], 'colb': [3,4]}
            ascii.write(data, Writer=ascii.Latex, latexdict=ascii.latex.latexdicts['template'])

        Some table styles are predefined in the dictionary
        ``ascii.latex.latexdicts``. The following generates in table in
        style preferred by A&A and some other journals::

            ascii.write(data, Writer=ascii.Latex, latexdict=ascii.latex.latexdicts['AA'])

        As an example, this generates a table, which spans all columns
        and is centered on the page::

            ascii.write(data, Writer=ascii.Latex, col_align='|lr|',
                        latexdict={'preamble': r'\begin{center}',
                                   'tablefoot': r'\end{center}',
                                   'tabletype': 'table*'})

    **caption** : Set table caption
        Shorthand for::

            latexdict['caption'] = caption

    **col_align** : Set the column alignment.
        If not present this will be auto-generated for centered
        columns. Shorthand for::

            latexdict['col_align'] = col_align

    '''
    _format_name = 'latex'
    _io_registry_format_aliases = ['latex']
    _io_registry_suffix = '.tex'
    _description = 'LaTeX table'

    def __init__(self, ignore_latex_commands=['hline', 'vspace', 'tableline'],
                 latexdict={}, caption='', col_align=None):

        core.BaseReader.__init__(self)
        self.header = LatexHeader()
        self.data = LatexData()

        self.header.splitter = LatexSplitter()
        self.data.splitter = LatexSplitter()
        self.data.header = self.header
        self.header.data = self.data
        self.latex = {}
        # The latex dict drives the format of the table and needs to be shared
        # with data and header
        self.header.latex = self.latex
        self.data.latex = self.latex
        self.latex['tabletype'] = 'table'
        self.latex.update(latexdict)
        if caption:
            self.latex['caption'] = caption
        if col_align:
            self.latex['col_align'] = col_align

        self.ignore_latex_commands = ignore_latex_commands
        self.header.comment = '%|' + '|'.join(
            [r'\\' + command for command in self.ignore_latex_commands])
        self.data.comment = self.header.comment

    def write(self, table=None):
        self.header.start_line = None
        self.data.start_line = None
        return core.BaseReader.write(self, table=table)


class AASTexHeader(LatexHeader):
    '''In a `deluxetable` some header keywords differ from standard LaTeX.

    This header is modified to take that into account.
    '''
    header_start = r'\tablehead'

    def start_line(self, lines):
        return find_latex_line(lines, r'\tablehead')

    def write(self, lines):
        if not 'col_align' in self.latex.keys():
            self.latex['col_align'] = len(self.cols) * 'c'

        lines.append(r'\begin{' + self.latex['tabletype'] + r'}{' + self.latex['col_align'] + r'}')
        add_dictval_to_list(self.latex, 'preamble', lines)
        if 'caption' in self.latex.keys():
            lines.append(r'\tablecaption{' + self.latex['caption'] + '}')
        tablehead = ' & '.join([r'\colhead{' + x.name + '}' for x in self.cols])
        if 'units' in self.latex.keys():
            tablehead += r'\\ ' + (self.splitter.join([self.latex[
                                   'units'].get(x.name, ' ') for x in self.cols]))
        lines.append(r'\tablehead{' + tablehead + '}')


class AASTexData(LatexData):
    '''In a `deluxetable` the data is enclosed in `\startdata` and `\enddata`
    '''
    data_start = r'\startdata'
    data_end = r'\enddata'

    def start_line(self, lines):
        return find_latex_line(lines, self.data_start) + 1

    def write(self, lines):
        lines.append(self.data_start)
        core.BaseData.write(self, lines)
        lines.append(self.data_end)
        add_dictval_to_list(self.latex, 'tablefoot', lines)
        lines.append(r'\end{' + self.latex['tabletype'] + r'}')


class AASTexHeaderSplitter(LatexSplitter):
    '''extract column names from a `deluxetable`

    This splitter expects the following LaTeX code **in a single line**:

        \tablehead{\colhead{col1} & ... & \colhead{coln}}
    '''
    def process_line(self, line):
        """extract column names from tablehead
        """
        line = line.split('%')[0]
        line = line.replace(r'\tablehead', '')
        line = line.strip()
        if (line[0] == '{') and (line[-1] == '}'):
            line = line[1:-1]
        else:
            raise core.InconsistentTableError(r'\tablehead is missing {}')
        return line.replace(r'\colhead', '')

    def join(self, vals):
        return ' & '.join([r'\colhead{' + str(x) + '}' for x in vals])


class AASTex(Latex):
    '''Write and read AASTeX tables.

    This class implements some AASTeX specific commands.
    AASTeX is used for the AAS (American Astronomical Society)
    publications like ApJ, ApJL and AJ.

    It derives from the ``Latex`` reader and accepts the same
    keywords.  However, the keywords ``header_start``, ``header_end``,
    ``data_start`` and ``data_end`` in ``latexdict`` have no effect.
    '''

    _format_name = 'aastex'
    _io_registry_format_aliases = ['aastex']
    _io_registry_suffix = ''  # AASTex inherits from Latex, so override this class attr
    _description = 'AASTeX deluxetable used for AAS journals'

    def __init__(self, **kwargs):
        Latex.__init__(self, **kwargs)
        self.header = AASTexHeader()
        self.data = AASTexData()
        self.header.comment = '%|' + '|'.join(
            [r'\\' + command for command in self.ignore_latex_commands])
        self.header.splitter = AASTexHeaderSplitter()
        self.data.splitter = LatexSplitter()
        self.data.comment = self.header.comment
        self.data.header = self.header
        self.header.data = self.data
        # The latex dict drives the format of the table and needs to be shared
        # with data and header
        self.header.latex = self.latex
        self.data.latex = self.latex
        # check if tabletype was explicitly set by the user
        if not (('latexdict' in kwargs) and ('tabletype' in kwargs['latexdict'])):
            self.latex['tabletype'] = 'deluxetable'
        self.header.comment = '%|' + '|'.join(
            [r'\\' + command for command in self.ignore_latex_commands])
        self.data.comment = self.header.comment
