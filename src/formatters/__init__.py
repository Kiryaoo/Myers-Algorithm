from formatters.base import (
    BaseFormatter,
    SimpleFormatter,
    FormatterConfig,
    FormatterFactory,
    ColorScheme,
    OutputWriter,
    OutputTarget,
    DiffHunk,
    HunkGenerator
)

from formatters.unified import (
    UnifiedFormatter,
    UnifiedDiffHeader,
    UnifiedDiffStats,
    UnifiedLineFormatter,
    HunkHeader,
    ContextDiffFormatter,
    NormalDiffFormatter,
    EDDiffFormatter,
    RCSDiffFormatter
)

from formatters.side_by_side import (
    SideBySideFormatter,
    SideBySideRow,
    SideBySideGenerator,
    SideBySideRowFormatter,
    SideBySideHeader,
    ColumnConfig,
    TextTruncator,
    LineNumberFormatter,
    GutterFormatter,
    CompactSideBySideFormatter,
    WordDiffFormatter,
    InlineDiffFormatter
)

from formatters.html import (
    HTMLFormatter,
    HTMLDocument,
    HTMLElement,
    DiffStylesheet,
    CSSStylesheet,
    DiffTableBuilder,
    SideBySideTableBuilder,
    SideBySideHTMLFormatter,
    GitHubStyleFormatter,
    JSONFormatter,
    XMLFormatter
)


__all__ = [
    "BaseFormatter",
    "SimpleFormatter",
    "FormatterConfig",
    "FormatterFactory",
    "ColorScheme",
    "OutputWriter",
    "OutputTarget",
    "DiffHunk",
    "HunkGenerator",
    "UnifiedFormatter",
    "UnifiedDiffHeader",
    "UnifiedDiffStats",
    "UnifiedLineFormatter",
    "HunkHeader",
    "ContextDiffFormatter",
    "NormalDiffFormatter",
    "EDDiffFormatter",
    "RCSDiffFormatter",
    "SideBySideFormatter",
    "SideBySideRow",
    "SideBySideGenerator",
    "SideBySideRowFormatter",
    "SideBySideHeader",
    "ColumnConfig",
    "TextTruncator",
    "LineNumberFormatter",
    "GutterFormatter",
    "CompactSideBySideFormatter",
    "WordDiffFormatter",
    "InlineDiffFormatter",
    "HTMLFormatter",
    "HTMLDocument",
    "HTMLElement",
    "DiffStylesheet",
    "CSSStylesheet",
    "DiffTableBuilder",
    "SideBySideTableBuilder",
    "SideBySideHTMLFormatter",
    "GitHubStyleFormatter",
    "JSONFormatter",
    "XMLFormatter"
]


def create_formatter(name: str, config: FormatterConfig = None) -> BaseFormatter:
    return FormatterFactory.create(name, config)


def get_available_formatters():
    return FormatterFactory.available()


def format_diff(
    script,
    file1: str,
    file2: str,
    formatter_name: str = "unified",
    config: FormatterConfig = None
) -> str:
    formatter = create_formatter(formatter_name, config)
    return formatter.format(script, file1, file2)
