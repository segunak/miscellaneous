# OneNote Export Roadmap

Date: 2026-06-05

This document captures the current product and engineering plan for improving OneNote to Markdown Exporter. It combines the active user requests in this repository with feature inspiration from the longer-running [alxnbl/onenote-md-exporter](https://github.com/alxnbl/onenote-md-exporter) project and its [release history](https://github.com/alxnbl/onenote-md-exporter/releases).

The goal is not to copy another exporter. The goal is to notice the preservation gaps that show up over time when real users migrate years of OneNote data, then build the right version of those ideas into this codebase.

## Scope And Principles

- Keep this project focused on a general-purpose Markdown exporter, not on one user's notebook shape.
- Keep current behavior backward-compatible unless a user explicitly opts into a new mode.
- Prefer first-class GUI and CLI options over hidden config files.
- Keep repeated exports predictable: generated Markdown and generated assets should overwrite cleanly when overwrite mode is enabled.
- Keep tests synthetic and generic. Do not encode private notebook names, user-specific examples, or assumptions from one environment.
- Borrow product ideas from other tools, not implementation code.
- Keep this app's direct OneNote XML conversion path. Do not add a Word/Pandoc conversion dependency unless a future requirement clearly justifies it.
- Keep GUI and CLI behavior aligned through shared export planning logic.

## Current Repository Requests

### Issue 1: Move Assets Folder

Reference: [Move Assets Folder? #1](https://github.com/segunak/one-note-to-markdown/issues/1)

Original request:

- Let users choose a different assets folder location instead of always using the default assets folder.
- Avoid requiring users to run search/replace against exported Markdown after export.

Implemented baseline:

- GUI and CLI support a custom assets folder.
- Missing folders are created automatically.
- Existing folders are reused.
- Paths where the assets target is an existing file are rejected.
- Markdown image links are generated relative to each exported Markdown page.
- Re-exporting should overwrite generated asset files cleanly.

Latest follow-up request:

- Add options for assets at each hierarchy level.
- Users may want images at the most granular page level, or grouped at a larger notebook level.

Recommended feature:

- Add asset organization modes:
  - `centralized`: current default, `<output>/assets` or a custom chosen folder.
  - `notebook`: each notebook export folder contains its own `assets` folder.
  - `section`: each section folder contains its own `assets` folder.
  - `page`: each page gets a page-specific asset folder beside the Markdown file.

Recommended page-level shape:

```text
Notebook/
  Section/
    Page.md
    Page_assets/
      image_0001.png
```

This keeps page Markdown and page assets portable without placing images directly among Markdown files.

### Issue 2: Pages To Folders And File Dates

Reference: [Pages to Folders and File Dates #2](https://github.com/segunak/one-note-to-markdown/issues/2)

User requests:

- Preserve notebook, section group, and section nesting as folders.
- Preserve page, subpage, and sub-subpage relationships.
- Make it clear when pages were associated with parent pages.
- Preserve OneNote created and modified dates in Explorer and/or the exported Markdown page.
- Keep the GUI workflow good for gradually moving selected pages out of OneNote.

Current state:

- The app already preserves OneNote subpage hierarchy through `pageLevel`.
- Parent pages export as Markdown files beside same-named folders containing child pages.

Current default layout:

```text
Section A/
  Parent Page.md
  Parent Page/
    Child Page.md
    Child Page/
      Grandchild Page.md
```

Recommendation:

- Keep this nested folder layout as the default.
- Document it clearly as the answer to the page/subpage request.
- Do not add flat prefixed filenames immediately. Prefix mode increases path length and collision risk.
- Consider an optional alternate layout later only if users ask for it after seeing the documented current behavior.

Potential future alternate layout:

```text
Section A/
  Parent Page/
    Parent Page.md
    Child Page.md
    Child Page/
      Grandchild Page.md
```

This is a stricter page-bundle model, but it would be a behavior change and should be opt-in.

## Immediate Roadmap

### 1. Asset Organization Modes

Priority: High

Add a central option model shared by GUI and CLI.

Proposed enum:

```csharp
public enum AssetOrganizationMode
{
    Centralized,
    Notebook,
    Section,
    Page
}
```

Behavior by mode:

| Mode | Asset folder | Custom assets path? | Best for |
| --- | --- | --- | --- |
| `centralized` | `<output>/assets` | Yes | Existing behavior, one asset root |
| `notebook` | `<output>/<Notebook>/assets` | No | Notebook-level portability |
| `section` | `<output>/<Notebook>/<Section>/assets` | No | Large notebooks with project or area sections |
| `page` | Beside page as `<Page>_assets` | No | Self-contained page bundles |

CLI proposal:

```powershell
OneNoteMarkdownExporter.exe --all --asset-organization centralized
OneNoteMarkdownExporter.exe --all --asset-organization notebook
OneNoteMarkdownExporter.exe --all --asset-organization section
OneNoteMarkdownExporter.exe --all --asset-organization page
```

GUI proposal:

- Add an asset organization selector near the existing assets folder field.
- Keep the custom assets folder picker enabled for `centralized` mode.
- Disable or annotate the custom assets field for `notebook`, `section`, and `page` modes.
- Show a concise preview of where assets will be placed.

Engineering notes:

- Reuse `AssetPathResolver.GetRelativeAssetsPath` for Markdown links.
- Keep `ExportPathSanitizer` responsible for generated folder names.
- Avoid duplicating asset path math in `ExportService` and `MainWindow.xaml.cs`.
- Create a shared path-planning helper before adding more options.
- The converter should receive the actual asset folder and relative link prefix. It should not infer asset placement mode by itself.

### 2. Date Preservation

Priority: High

Add date metadata to the export model.

Proposed fields:

```csharp
public DateTime? CreatedTime { get; set; }
public DateTime? LastModifiedTime { get; set; }
```

Parsing strategy:

- Parse dates from OneNote hierarchy XML returned by `GetHierarchy`.
- Microsoft documents that hierarchy XML includes node properties such as title, ID, and last-modified time.
- For pages, parse likely attributes such as `dateTime` and `lastModifiedTime`.
- Parse defensively by local attribute name so schema/version differences do not break export.
- Optionally supplement from page content XML returned by `GetPageContent`.

Preservation strategy:

- Set exported Markdown `CreationTime` and `LastWriteTime` after the Markdown file is fully written.
- Run linting/formatting before setting file timestamps so formatting does not reset the modified time.
- If timestamp setting fails for one page, log a warning/failure detail and continue the export.

CLI proposal:

```powershell
OneNoteMarkdownExporter.exe --all --preserve-dates
OneNoteMarkdownExporter.exe --all --no-preserve-dates
OneNoteMarkdownExporter.exe --all --date-metadata yaml
OneNoteMarkdownExporter.exe --all --date-metadata none
```

GUI proposal:

- Checkbox: preserve OneNote dates as file timestamps.
- Optional checkbox or dropdown: add Markdown metadata.

YAML front matter proposal:

```yaml
---
title: Page title
created: 2024-01-15T10:30:00Z
updated: 2024-02-20T14:45:00Z
oneNotePageId: page-id
---
```

Default recommendation:

- Preserve file timestamps by default if dates are available.
- Keep YAML front matter opt-in because it changes Markdown content.

### 3. Page/Subpage Documentation

Priority: High

Use OneNote terminology in the docs:

- Page
- Subpage
- Sub-subpage

Explain how the exporter maps these to folders.

Add examples for:

- Full notebook export.
- Section group export.
- Parent page with subpages.
- Exporting only a subpage while preserving its parent folder context.
- Page-level assets interacting with subpage folders.

## Preservation Backlog Inspired By alxnbl Releases

The [alxnbl/onenote-md-exporter releases](https://github.com/alxnbl/onenote-md-exporter/releases) show a useful maturity path for OneNote migration tools. Their project repeatedly improved data preservation, diagnostics, and output organization over several years.

### 4. OneNote Internal Link Conversion

Priority: High after asset/date work

References:

- [v1.6.0 release](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [OneNoteLinksHandlingEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/OneNoteLinksHandlingEnum.cs)
- [OneNoteLinkTranslatorService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/OneNoteLinkTranslatorService.cs)

Proposed option:

```text
keep      Keep original onenote:// links
markdown  Convert known page links to relative Markdown links
wikilink  Convert known page links to [[wiki links]]
remove    Keep the link text but remove the OneNote URL
```

Implementation approach:

- Build a page ID to exported path map before converting page content.
- Resolve internal links after export paths are planned.
- Convert only links that can be resolved safely.
- Log unresolved OneNote links in verbose output or warnings.

Known limitations to document:

- Cross-notebook links may not resolve if the target notebook was not exported.
- Section links may need a different mapping than page links.
- Links to objects inside a page may not map cleanly to Markdown anchors.

### 5. Tags And Checkboxes

Priority: Medium-high

References:

- [v1.6.0 release](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [TagsDefMap](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/TagsDefMap.cs)

Feature goals:

- Convert OneNote task tags to Markdown checkboxes.
- Preserve common semantic tags such as important, question, definition, and reminder in readable text.
- Avoid obscure symbols unless users opt into a symbol-preserving mode.

Potential output:

```markdown
- [ ] Follow up with team
- [x] Completed migration task
Important: Confirm archive location
Question: Should this page be split?
```

Testing needs:

- Incomplete task.
- Completed task.
- Multiple tags on a line.
- Tags inside lists and tables.

### 6. Embedded File And Media Attachments

Priority: Medium-high

References:

- [v0.2 release: file attachments](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.2)
- [v1.5.0 release: media attachments](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)
- [Attachment model](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/Attachement.cs)

Feature goals:

- Export embedded non-image files.
- Export common media attachments when exposed by OneNote.
- Link attachments from Markdown near their original position when possible.
- Avoid filename collisions.

Potential asset structure:

```text
Page.md
Page_assets/
  image_0001.png
  attachment_0001.pdf
  audio_0001.mp3
```

Potential Markdown output:

```markdown
[Project brief](Page_assets/project-brief.pdf)
[Meeting recording](Page_assets/meeting-recording.mp3)
```

Design questions:

- Should attachments share the selected asset organization mode with images? Recommendation: yes.
- Should image and file assets be separated? Recommendation: not initially; keep one asset folder per selected organization level.

### 7. Folded Or Collapsed Content

Priority: Medium-high

References:

- [v1.5.0 release: folded paragraph content no longer lost](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)

Current project context:

- The GUI already has a setting to try expanding collapsed paragraphs.
- This needs stronger validation and clearer user-facing behavior.

Feature goals:

- Avoid silently losing collapsed content.
- If content cannot be expanded because a notebook is read-only or protected, warn clearly.
- Add tests around collapsed paragraph XML.

Possible user-facing behavior:

- `Expanded collapsed paragraphs: 12`
- `Could not expand collapsed content on 3 read-only pages`

### 8. Highlights And Styling

Priority: Medium

References:

- [v1.4.0 release: text highlight](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)
- [README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)

Feature goals:

- Preserve highlight semantics where possible.
- Prefer Markdown highlight syntax `==text==` only if the user's target Markdown editor supports it.
- Offer HTML-preserving output later for colors/backgrounds that Markdown cannot represent.

Potential modes:

```text
plain     Prefer Markdown/plain text
html      Preserve styling with inline HTML where needed
minimal   Drop styling that cannot be represented cleanly
```

Recommendation:

- Do not add broad styling modes until the core export organization/date/link work is stable.
- Add focused tests for highlight conversion first.

### 9. Complex Tables And Images In Tables

Priority: Medium

References:

- [v1.6.0 release: images in table cells](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [alxnbl README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)

Feature goals:

- Simple tables should export as Markdown tables when possible.
- Complex tables can remain HTML if that preserves content better.
- Images inside table cells should have valid links and should render.

Testing needs:

- Simple table.
- Nested formatting in table cells.
- Image in table cell.
- Multiple images in one table.
- Table with line breaks.

### 10. Error Isolation And Execution Reports

Priority: Medium

References:

- [v1.3.0 release: corrupted pages do not block export](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.3.0 release: execution report](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.6.0 release: highlighted errors](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)

Current project context:

- The GUI already has a Logs tab and Failures tab.
- CLI exports return failure counts.

Feature goals:

- One failed page should not abort the whole export.
- Failures should show page name, OneNote ID, target path, and error.
- Final summary should include exported, failed, skipped, warnings, and output path.
- CLI should write errors to stderr and return a non-zero exit code when failures occur.

Example final report:

```text
Export Summary
Pages exported: 128
Pages failed: 3
Warnings: 5
Output: C:\Users\me\Downloads\OneNoteExport
Failure details: see Failures tab or CLI output above
```

### 11. Startup And OneNote Diagnostics

Priority: Medium

References:

- [v1.3.0 release: better startup error handling](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.4.0 release: enhanced startup error if OneNote crashes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)
- [OneNote Application interface](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote)

Feature goals:

- Detect and explain common OneNote COM startup failures.
- Explain that the desktop OneNote app is required.
- Explain sync issues for cloud notebooks.
- Explain protected/locked section behavior.

Potential messages:

- `Could not initialize OneNote Desktop. Open OneNote once, make sure notebooks are loaded, then try again.`
- `This page may not be fully synced. Open it in OneNote and force sync before exporting.`
- `Protected section is locked. Unlock it in OneNote before exporting.`

### 12. Large Notebook Performance

Priority: Medium

References:

- [v1.5.0 release: memory optimization](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)

Feature goals:

- Keep large 15+ year notebook exports stable.
- Avoid holding unnecessary page content in memory.
- Stream or process page-by-page where possible.
- Keep progress accurate and responsive.

Testing needs:

- Synthetic hierarchy with many notebooks, sections, and pages.
- Deep subpage trees.
- Many images/assets.
- Cancellation during a long export.

### 13. Path Length And Naming Controls

Priority: Medium

References:

- [v1.3.0 release: max page title length setting](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.4.0 release: path errors](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)

Current project context:

- This project already has robust Windows-safe path sanitization.
- It handles invalid characters, trailing spaces/periods, reserved names, and long path shortening.

Future improvements:

- Add optional max filename/component length controls if users hit deep hierarchy path limits.
- Keep generated shortening deterministic.
- Preserve readable names when path length allows.

### 14. Markdown Output Quality

Priority: Medium

References:

- [v0.5.0 release: line break behavior](https://github.com/alxnbl/onenote-md-exporter/releases/tag/0.5.0)
- [v1.2.0 release: cleaner line breaks](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.2.0)
- [markdownlint-cli](https://github.com/DavidAnson/markdownlint-cli)

Current project context:

- This project already bundles markdownlint-cli.
- Earlier work identified trailing newline and bare URL wrapping as important output-quality details.

Feature goals:

- Keep trailing newlines correct.
- Keep bare URLs lint-clean or intentionally configured.
- Avoid duplicate/strange blank lines.
- Keep Markdown readable without destroying intentional OneNote spacing.

### 15. Feature And Limitations Matrix

Priority: High documentation work

References:

- [alxnbl README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)
- [alxnbl Joplin migration comparison](https://github.com/alxnbl/onenote-md-exporter/blob/main/doc/migration-to-joplin.md)

Add a README table like this:

| OneNote feature | Current support | Planned improvement | Notes |
| --- | --- | --- | --- |
| Notebook hierarchy | Supported | Documentation examples | Folders |
| Section groups | Supported | Documentation examples | Nested folders |
| Pages/subpages | Supported | Document terminology | Uses `pageLevel` |
| Images | Supported | Asset organization modes | Relative links |
| File attachments | Partial/unknown | Export embedded files | Needs research/tests |
| OneNote dates | Not yet | File timestamps + YAML | Issue #2 |
| Internal links | Not yet | Markdown/wikilink conversion | Later feature |
| Tags/checklists | Partial/unknown | Markdown checkboxes/tags | Later feature |
| Folded content | Partial | Stronger preservation/warnings | Needs tests |
| Simple tables | Supported/partial | Verify | Needs tests |
| Complex tables | Partial | HTML fallback | Needs tests |
| Highlights/colors | Partial | Highlight/styling modes | Later feature |
| Handwriting/ink | Unsupported/partial | Document limitation | May not be practical |
| Protected sections | Requires unlock | Better warnings | User must unlock |

## Lower Priority Or Deferred Ideas

### Joplin Export Mode

References:

- [alxnbl Joplin migration guide](https://github.com/alxnbl/onenote-md-exporter/blob/main/doc/migration-to-joplin.md)
- [Joplin raw directory references in alxnbl code](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/JoplinExportService.cs)

This could be useful eventually, but it is a bigger product direction. It should not block making the generic Markdown exporter excellent.

### Markdown Flavor Modes

Possible future modes:

- GitHub-flavored Markdown.
- Strict/CommonMark-oriented Markdown.
- Wiki-link-oriented Markdown.
- HTML-preserving Markdown.

Recommendation:

- Add only when users have clear target-app needs.
- Avoid creating too many options before the core preservation work is reliable.

### Open Output Folder After Export

Small GUI convenience:

- Open the output folder after successful export.
- Possibly make this optional.

This is useful, but not urgent.

## Engineering Architecture Plan

### Shared Export Planning

Current pressure:

- GUI and CLI export traversal have similar but separate logic.
- Adding asset/date/link/layout modes risks divergence.

Recommendation:

- Add shared export planning helpers before adding many options.
- A planning object should know:
  - Output root.
  - Sanitized notebook path.
  - Sanitized section path.
  - Page Markdown path.
  - Page folder path for subpages.
  - Asset folder path for the selected asset mode.
  - Relative asset link prefix for the Markdown file.

Possible types:

```csharp
public sealed class PageExportContext
{
    public OneNoteItem Page { get; init; }
    public string MarkdownFilePath { get; init; }
    public string MarkdownFolderPath { get; init; }
    public string AssetsFolderPath { get; init; }
    public string RelativeAssetsPath { get; init; }
}
```

```csharp
public sealed class ExportPathPlanner
{
    public PageExportContext CreatePageContext(...);
}
```

### Date Handling Service

Add a focused helper for setting timestamps:

```csharp
public interface IFileTimestampService
{
    void ApplyTimestamps(string filePath, DateTime? created, DateTime? modified);
}
```

Reasons:

- Keeps Windows file timestamp behavior isolated.
- Makes tests easier.
- Allows soft failure handling in one place.

### Link Conversion Service

Add a service after path planning exists:

```csharp
public sealed class OneNoteLinkConversionService
{
    public void RegisterPage(string oneNotePageId, string markdownPath, string title);
    public string ConvertLinks(string markdown, OneNoteLinkMode mode);
}
```

The service needs the final planned Markdown paths before conversion.

## Code Areas

Core option model:

- [ExportOptions.cs](../OneNoteMarkdownExporter/Services/ExportOptions.cs)

Export traversal and planning:

- [ExportService.cs](../OneNoteMarkdownExporter/Services/ExportService.cs)
- [MainWindow.xaml.cs](../OneNoteMarkdownExporter/MainWindow.xaml.cs)
- [ExportSelectionHelper.cs](../OneNoteMarkdownExporter/Services/ExportSelectionHelper.cs)

GUI and CLI:

- [MainWindow.xaml](../OneNoteMarkdownExporter/MainWindow.xaml)
- [CliHandler.cs](../OneNoteMarkdownExporter/Services/CliHandler.cs)

Paths and assets:

- [AssetPathResolver.cs](../OneNoteMarkdownExporter/Services/AssetPathResolver.cs)
- [ExportPathSanitizer.cs](../OneNoteMarkdownExporter/Services/ExportPathSanitizer.cs)

OneNote model and metadata:

- [OneNoteItem.cs](../OneNoteMarkdownExporter/Models/OneNoteItem.cs)
- [OneNoteService.cs](../OneNoteMarkdownExporter/Services/OneNoteService.cs)

Markdown conversion:

- [OneNoteXmlToMarkdownConverter.cs](../OneNoteMarkdownExporter/Services/OneNoteXmlToMarkdownConverter.cs)

Failure reporting:

- [ExportFailureFormatter.cs](../OneNoteMarkdownExporter/Services/ExportFailureFormatter.cs)

Public documentation:

- [README.md](../README.md)

## Test Plan

General rule:

- Tests must use synthetic and generic notebook, section, page, subpage, asset, and attachment names.
- Never encode behavior specific to a real private notebook.

### Required Tests For Immediate Work

Asset organization:

- Centralized default assets path.
- Centralized custom absolute path.
- Centralized custom relative path.
- Existing file rejected as assets folder.
- Notebook-level assets.
- Section-level assets.
- Page-level assets.
- Correct relative links from pages at different depths.
- Re-export overwrites generated asset files.

Dates:

- Parse `dateTime` from hierarchy XML.
- Parse `lastModifiedTime` from hierarchy XML.
- Missing dates stay null.
- Invalid dates do not break hierarchy parsing.
- File timestamps are set after Markdown write/lint.
- YAML front matter appears only when enabled.

Subpages:

- Parent page with child page.
- Parent page with child and grandchild.
- Export only selected subpage while preserving parent folder context.
- Do not mutate UI selection state during export.

### Tests For Backlog Features

Links:

- Keep original OneNote links.
- Convert resolvable page link to relative Markdown link.
- Convert resolvable page link to wikilink.
- Remove unresolved links but keep display text.
- Cross-notebook unresolved link is logged or warned.

Tags:

- Incomplete checkbox.
- Completed checkbox.
- Important/question/reminder tags.
- Tags inside lists.

Attachments:

- Embedded PDF/file.
- Media attachment.
- Duplicate attachment names.
- Attachment links respect selected asset organization mode.

Tables/styling:

- Simple table.
- Complex table fallback.
- Image in table cell.
- Highlight conversion.

Reliability:

- One page failure does not stop export.
- Final summary contains failures and warnings.
- Startup COM exception returns a useful message.

Validation command:

```powershell
dotnet test .\OneNoteMarkdownExporter.Tests\OneNoteMarkdownExporter.Tests.csproj
```

Manual validation scenarios:

- Export a synthetic notebook with nested section groups, subpages, images, links, tags, collapsed content, duplicate names, and long/special paths.
- Re-export to the same output with overwrite enabled.
- Inspect links in a Markdown viewer.
- Inspect created/modified timestamps in Windows Explorer.
- Confirm failures are shown in the GUI Failures tab and CLI summary.

## Proposed Implementation Order

1. Add option types and defaults for asset organization and date preservation.
2. Add shared path planning for page Markdown paths and asset folders.
3. Implement asset organization modes in CLI export.
4. Wire asset organization modes into GUI export.
5. Add date parsing to the OneNote model/service.
6. Apply file timestamps after Markdown write/lint.
7. Add optional YAML front matter.
8. Update README with issue #1/#2 docs and examples.
9. Add feature/limitations matrix.
10. Add internal link conversion.
11. Add file/media attachment export.
12. Add tags/checklists/highlights preservation.
13. Harden folded content and complex tables.
14. Improve diagnostics, startup messages, and final reports.
15. Revisit larger target-app modes such as Joplin export.

## Proposed Milestones

### Milestone 1: Issue #1 And #2 Completion

Deliver:

- Asset organization modes.
- Date parsing.
- File timestamp preservation.
- Optional YAML front matter.
- README examples for assets, subpages, and dates.
- Tests for asset paths, date parsing, timestamps, and repeated export behavior.

### Milestone 2: Trust And Documentation

Deliver:

- Feature/limitations matrix.
- Better final export report.
- Expanded troubleshooting for OneNote COM, sync, locked sections, and missing content.
- Clear issue response language explaining what is supported.

### Milestone 3: Migration Preservation

Deliver:

- Embedded file attachments.
- Media attachments where OneNote exposes binary content.
- OneNote tag and checkbox translation.
- Highlight preservation.

### Milestone 4: Knowledge Graph Preservation

Deliver:

- Internal OneNote link conversion.
- Link mode options for Markdown links and wikilinks.
- Cross-selection link warnings.

### Milestone 5: Hardening For Large Legacy Notebooks

Deliver:

- Collapsed content hardening.
- Complex table and image-in-table tests.
- Optional max name length controls.
- Memory and progress improvements for very large exports.

## Release Note Themes

When these ship, release notes should be curated rather than only auto-generated.

Suggested release note groups:

- Export organization.
- Date preservation.
- Page/subpage hierarchy documentation.
- Reliability and diagnostics.
- Markdown preservation improvements.
- Known limitations.

Example for the immediate release:

```markdown
## Highlights

- Added asset organization modes: centralized, notebook, section, and page.
- Added OneNote date preservation as Windows file timestamps.
- Added optional YAML front matter for created/updated page metadata.
- Documented how OneNote pages, subpages, and sub-subpages export to folders.

## Notes

- Existing centralized asset behavior remains the default.
- Custom asset folder paths apply to centralized mode.
- YAML metadata is opt-in because it changes Markdown content.
```

## Deliberate Non-Goals For Now

- Do not add a Pandoc/Word dependency just because another exporter uses it.
- Do not require users to edit JSON settings by hand for major options.
- Do not change the default page/subpage layout until there is clear demand.
- Do not make Joplin/raw export part of the immediate issue #1/#2 work.
- Do not add notebook-specific logic or tests based on one user's real notebooks.

## Reference Links

### This Repository

- [Repository](https://github.com/segunak/one-note-to-markdown)
- [Issue #1: Move Assets Folder?](https://github.com/segunak/one-note-to-markdown/issues/1)
- [Issue #2: Pages to Folders and File Dates](https://github.com/segunak/one-note-to-markdown/issues/2)
- [Releases](https://github.com/segunak/one-note-to-markdown/releases)
- [README](../README.md)

### Comparable Exporter

- [alxnbl/onenote-md-exporter](https://github.com/alxnbl/onenote-md-exporter)
- [alxnbl releases](https://github.com/alxnbl/onenote-md-exporter/releases)
- [alxnbl README](https://github.com/alxnbl/onenote-md-exporter/blob/main/README.md)
- [alxnbl README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)
- [alxnbl Joplin migration guide](https://github.com/alxnbl/onenote-md-exporter/blob/main/doc/migration-to-joplin.md)

### Comparable Exporter Releases

- [v1.6.0: OneNote link conversion, tag translation, table image fix](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [v1.5.0: media attachments, folded paragraphs, encoding, memory optimization](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)
- [v1.4.0: highlights, GUID attachment names, path fixes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)
- [v1.3.0: corrupted page isolation, execution report, max page title length](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.2.0: cleaner line breaks and Joplin hierarchy](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.2.0)
- [v1.1.0: page hierarchy and resource folder settings](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.1.0)
- [v1.0.0: YAML front matter and duplicate title fixes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.0.0)
- [v0.5.0: line break behavior and bundled Pandoc](https://github.com/alxnbl/onenote-md-exporter/releases/tag/0.5.0)
- [v0.4.0: command-line parameters and image references](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.4.0)
- [v0.3.1: temp folder fix](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.3.1)
- [v0.3: self-contained release](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.3)
- [v0.2.1: more logs and minor fixes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.2.1)
- [v0.2: file attachments](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.2)
- [v0.1: initial prerelease](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.1)

### Comparable Exporter Code References

- [ResourceFolderLocationEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/ResourceFolderLocationEnum.cs)
- [PageHierarchyEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/PageHierarchyEnum.cs)
- [OneNoteLinksHandlingEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/OneNoteLinksHandlingEnum.cs)
- [OneNoteLinkTranslatorService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/OneNoteLinkTranslatorService.cs)
- [MdExportService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/MdExportService.cs)
- [ExportServiceBase](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/ExportServiceBase.cs)
- [AppSettings](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Infrastructure/AppSettings.cs)
- [TagsDefMap](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/TagsDefMap.cs)
- [JoplinExportService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/JoplinExportService.cs)
- [Attachment model](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/Attachement.cs)

### Microsoft And Tooling References

- [Microsoft OneNote Application interface](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote)
- [OneNote GetHierarchy method](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote#gethierarchy-method)
- [OneNote GetPageContent method](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote#getpagecontent-method)
- [OneNote GetBinaryPageContent method](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote#getbinarypagecontent-method)
- [OneNote desktop version guidance](https://support.microsoft.com/en-us/office/what-s-the-difference-between-the-onenote-versions-a624e692-b78b-4c09-b07f-46181958118f)
- [OneNote for Windows 10 support status](https://support.microsoft.com/en-us/office/what-is-happening-to-onenote-for-windows-10-2b453bfe-66bc-4ab2-9118-01e7eb54d2d6)
- [WPF overview](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/overview/)
- [COM interop in .NET](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/cominterop)
- [markdownlint-cli](https://github.com/DavidAnson/markdownlint-cli)
- [System.CommandLine](https://github.com/dotnet/command-line-api)# OneNote Export Roadmap

Date: 2026-06-05

This document captures the current product and engineering plan for improving OneNote to Markdown Exporter. It combines the active user requests in this repository with feature inspiration from the longer-running [alxnbl/onenote-md-exporter](https://github.com/alxnbl/onenote-md-exporter) project and its [release history](https://github.com/alxnbl/onenote-md-exporter/releases).

The goal is not to copy another exporter. The goal is to notice the preservation gaps that show up over time when real users migrate years of OneNote data, then build the right version of those ideas into this codebase.

## Scope And Principles

- Keep this project focused on a general-purpose Markdown exporter, not on one user's notebook shape.
- Keep current behavior backward-compatible unless a user explicitly opts into a new mode.
- Prefer first-class GUI and CLI options over hidden config files.
- Keep repeated exports predictable: generated Markdown and generated assets should overwrite cleanly when overwrite mode is enabled.
- Keep tests synthetic and generic. Do not encode private notebook names, user-specific examples, or assumptions from one environment.
- Borrow product ideas from other tools, not implementation code.
- Keep this app's direct OneNote XML conversion path. Do not add a Word or Pandoc conversion dependency unless a future requirement clearly justifies it.
- Keep GUI and CLI behavior aligned through shared export planning logic.

## Current Repository Requests

### Issue 1: Move Assets Folder

Reference: [Move Assets Folder? #1](https://github.com/segunak/one-note-to-markdown/issues/1)

Original request:

- Let users choose a different assets folder location instead of always using the default assets folder.
- Avoid requiring users to run search/replace against exported Markdown after export.

Implemented baseline:

- GUI and CLI support a custom assets folder.
- Missing folders are created automatically.
- Existing folders are reused.
- Paths where the assets target is an existing file are rejected.
- Markdown image links are generated relative to each exported Markdown page.
- Re-exporting should overwrite generated asset files cleanly.

Latest follow-up request:

- Add options for assets at each hierarchy level.
- Users may want images at the most granular page level, or grouped at a larger notebook level.

Recommended feature:

- Add asset organization modes:
  - `centralized`: current default, `<output>/assets` or a custom chosen folder.
  - `notebook`: each notebook export folder contains its own `assets` folder.
  - `section`: each section folder contains its own `assets` folder.
  - `page`: each page gets a page-specific asset folder beside the Markdown file.

Recommended page-level shape:

```text
Notebook/
  Section/
    Page.md
    Page_assets/
      image_0001.png
```

This keeps page Markdown and page assets portable without placing images directly among Markdown files.

### Issue 2: Pages To Folders And File Dates

Reference: [Pages to Folders and File Dates #2](https://github.com/segunak/one-note-to-markdown/issues/2)

User requests:

- Preserve notebook, section group, and section nesting as folders.
- Preserve page, subpage, and sub-subpage relationships.
- Make it clear when pages were associated with parent pages.
- Preserve OneNote created and modified dates in Explorer and/or the exported Markdown page.
- Keep the GUI workflow good for gradually moving selected pages out of OneNote.

Current state:

- The app already preserves OneNote subpage hierarchy through `pageLevel`.
- Parent pages export as Markdown files beside same-named folders containing child pages.

Current default layout:

```text
Section A/
  Parent Page.md
  Parent Page/
    Child Page.md
    Child Page/
      Grandchild Page.md
```

Recommendation:

- Keep this nested folder layout as the default.
- Document it clearly as the answer to the page/subpage request.
- Do not add flat prefixed filenames immediately. Prefix mode increases path length and collision risk.
- Consider an optional alternate layout later only if users ask for it after seeing the documented current behavior.

Potential future alternate layout:

```text
Section A/
  Parent Page/
    Parent Page.md
    Child Page.md
    Child Page/
      Grandchild Page.md
```

This is a stricter page-bundle model, but it would be a behavior change and should be opt-in.

## Immediate Roadmap

### 1. Asset Organization Modes

Priority: High

Add a central option model shared by GUI and CLI.

Proposed enum:

```csharp
public enum AssetOrganizationMode
{
    Centralized,
    Notebook,
    Section,
    Page
}
```

Behavior by mode:

| Mode | Asset folder | Custom assets path? | Best for |
| --- | --- | --- | --- |
| `centralized` | `<output>/assets` | Yes | Existing behavior, one asset root |
| `notebook` | `<output>/<Notebook>/assets` | No | Notebook-level portability |
| `section` | `<output>/<Notebook>/<Section>/assets` | No | Large notebooks with project or area sections |
| `page` | beside page as `<Page>_assets` | No | Self-contained page bundles |

CLI proposal:

```powershell
OneNoteMarkdownExporter.exe --all --asset-organization centralized
OneNoteMarkdownExporter.exe --all --asset-organization notebook
OneNoteMarkdownExporter.exe --all --asset-organization section
OneNoteMarkdownExporter.exe --all --asset-organization page
```

GUI proposal:

- Add an asset organization selector near the existing assets folder field.
- Keep the custom assets folder picker enabled for `centralized` mode.
- Disable or annotate the custom assets field for `notebook`, `section`, and `page` modes.
- Show a concise preview of where assets will be placed.

Engineering notes:

- Reuse `AssetPathResolver.GetRelativeAssetsPath` for Markdown links.
- Keep `ExportPathSanitizer` responsible for generated folder names.
- Avoid duplicating asset path math in `ExportService` and `MainWindow.xaml.cs`.
- Create a shared path-planning helper before adding more options.
- The converter should receive the actual asset folder and relative link prefix. It should not infer asset placement mode by itself.

### 2. Date Preservation

Priority: High

Add date metadata to the export model.

Proposed fields:

```csharp
public DateTime? CreatedTime { get; set; }
public DateTime? LastModifiedTime { get; set; }
```

Parsing strategy:

- Parse dates from OneNote hierarchy XML returned by `GetHierarchy`.
- Microsoft documents that hierarchy XML includes node properties such as title, ID, and last-modified time.
- For pages, parse likely attributes such as `dateTime` and `lastModifiedTime`.
- Parse defensively by local attribute name so schema/version differences do not break export.
- Optionally supplement from page content XML returned by `GetPageContent`.

Preservation strategy:

- Set exported Markdown `CreationTime` and `LastWriteTime` after the Markdown file is fully written.
- Run linting/formatting before setting file timestamps so formatting does not reset the modified time.
- If timestamp setting fails for one page, log a warning/failure detail and continue the export.

CLI proposal:

```powershell
OneNoteMarkdownExporter.exe --all --preserve-dates
OneNoteMarkdownExporter.exe --all --no-preserve-dates
OneNoteMarkdownExporter.exe --all --date-metadata yaml
OneNoteMarkdownExporter.exe --all --date-metadata none
```

GUI proposal:

- Checkbox: preserve OneNote dates as file timestamps.
- Optional checkbox or dropdown: add Markdown metadata.

YAML front matter proposal:

```yaml
---
title: Page title
created: 2024-01-15T10:30:00Z
updated: 2024-02-20T14:45:00Z
oneNotePageId: page-id
---
```

Default recommendation:

- Preserve file timestamps by default if dates are available.
- Keep YAML front matter opt-in because it changes Markdown content.

### 3. Page/Subpage Documentation

Priority: High

Use OneNote terminology in the docs:

- Page
- Subpage
- Sub-subpage

Explain how the exporter maps these to folders.

Add examples for:

- Full notebook export.
- Section group export.
- Parent page with subpages.
- Exporting only a subpage while preserving its parent folder context.
- Page-level assets interacting with subpage folders.

## Preservation Backlog Inspired By alxnbl Releases

The [alxnbl/onenote-md-exporter releases](https://github.com/alxnbl/onenote-md-exporter/releases) show a useful maturity path for OneNote migration tools. Their project repeatedly improved data preservation, diagnostics, and output organization over several years.

### 4. OneNote Internal Link Conversion

Priority: High after asset/date work

References:

- [v1.6.0 release](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [OneNoteLinksHandlingEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/OneNoteLinksHandlingEnum.cs)
- [OneNoteLinkTranslatorService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/OneNoteLinkTranslatorService.cs)

Proposed option:

```text
keep      Keep original onenote:// links
markdown  Convert known page links to relative Markdown links
wikilink  Convert known page links to [[wiki links]]
remove    Keep the link text but remove the OneNote URL
```

Implementation approach:

- Build a page ID to exported path map before converting page content.
- Resolve internal links after export paths are planned.
- Convert only links that can be resolved safely.
- Log unresolved OneNote links in verbose output or warnings.

Known limitations to document:

- Cross-notebook links may not resolve if the target notebook was not exported.
- Section links may need a different mapping than page links.
- Links to objects inside a page may not map cleanly to Markdown anchors.

### 5. Tags And Checkboxes

Priority: Medium-high

References:

- [v1.6.0 release](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [TagsDefMap](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/TagsDefMap.cs)

Feature goals:

- Convert OneNote task tags to Markdown checkboxes.
- Preserve common semantic tags such as important, question, definition, and reminder in readable text.
- Avoid obscure symbols unless users opt into a symbol-preserving mode.

Potential output:

```markdown
- [ ] Follow up with team
- [x] Completed migration task
Important: Confirm archive location
Question: Should this page be split?
```

Testing needs:

- Incomplete task.
- Completed task.
- Multiple tags on a line.
- Tags inside lists and tables.

### 6. Embedded File And Media Attachments

Priority: Medium-high

References:

- [v0.2 release: file attachments](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.2)
- [v1.5.0 release: media attachments](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)
- [Attachment model](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/Attachement.cs)

Feature goals:

- Export embedded non-image files.
- Export common media attachments when exposed by OneNote.
- Link attachments from Markdown near their original position when possible.
- Avoid filename collisions.

Potential asset structure:

```text
Page.md
Page_assets/
  image_0001.png
  attachment_0001.pdf
  audio_0001.mp3
```

Potential Markdown output:

```markdown
[Project brief](Page_assets/project-brief.pdf)
[Meeting recording](Page_assets/meeting-recording.mp3)
```

Design questions:

- Should attachments share the selected asset organization mode with images? Recommendation: yes.
- Should image and file assets be separated? Recommendation: not initially; keep one asset folder per selected organization level.

### 7. Folded Or Collapsed Content

Priority: Medium-high

References:

- [v1.5.0 release: folded paragraph content no longer lost](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)

Current project context:

- The GUI already has a setting to try expanding collapsed paragraphs.
- This needs stronger validation and clearer user-facing behavior.

Feature goals:

- Avoid silently losing collapsed content.
- If content cannot be expanded because a notebook is read-only or protected, warn clearly.
- Add tests around collapsed paragraph XML.

Possible user-facing behavior:

- `Expanded collapsed paragraphs: 12`
- `Could not expand collapsed content on 3 read-only pages`

### 8. Highlights And Styling

Priority: Medium

References:

- [v1.4.0 release: text highlight](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)
- [README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)

Feature goals:

- Preserve highlight semantics where possible.
- Prefer Markdown highlight syntax `==text==` only if the user's target Markdown editor supports it.
- Offer HTML-preserving output later for colors/backgrounds that Markdown cannot represent.

Potential modes:

```text
plain     Prefer Markdown/plain text
html      Preserve styling with inline HTML where needed
minimal   Drop styling that cannot be represented cleanly
```

Recommendation:

- Do not add broad styling modes until the core export organization/date/link work is stable.
- Add focused tests for highlight conversion first.

### 9. Complex Tables And Images In Tables

Priority: Medium

References:

- [v1.6.0 release: images in table cells](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [alxnbl README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)

Feature goals:

- Simple tables should export as Markdown tables when possible.
- Complex tables can remain HTML if that preserves content better.
- Images inside table cells should have valid links and should render.

Testing needs:

- Simple table.
- Nested formatting in table cells.
- Image in table cell.
- Multiple images in one table.
- Table with line breaks.

### 10. Error Isolation And Execution Reports

Priority: Medium

References:

- [v1.3.0 release: corrupted pages do not block export](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.3.0 release: execution report](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.6.0 release: highlighted errors](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)

Current project context:

- The GUI already has a Logs tab and Failures tab.
- CLI exports return failure counts.

Feature goals:

- One failed page should not abort the whole export.
- Failures should show page name, OneNote ID, target path, and error.
- Final summary should include exported, failed, skipped, warnings, and output path.
- CLI should write errors to stderr and return a non-zero exit code when failures occur.

Example final report:

```text
Export Summary
Pages exported: 128
Pages failed: 3
Warnings: 5
Output: C:\Users\me\Downloads\OneNoteExport
Failure details: see Failures tab or CLI output above
```

### 11. Startup And OneNote Diagnostics

Priority: Medium

References:

- [v1.3.0 release: better startup error handling](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.4.0 release: enhanced startup error if OneNote crashes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)
- [OneNote Application interface](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote)

Feature goals:

- Detect and explain common OneNote COM startup failures.
- Explain that the desktop OneNote app is required.
- Explain sync issues for cloud notebooks.
- Explain protected/locked section behavior.

Potential messages:

- `Could not initialize OneNote Desktop. Open OneNote once, make sure notebooks are loaded, then try again.`
- `This page may not be fully synced. Open it in OneNote and force sync before exporting.`
- `Protected section is locked. Unlock it in OneNote before exporting.`

### 12. Large Notebook Performance

Priority: Medium

References:

- [v1.5.0 release: memory optimization](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)

Feature goals:

- Keep large 15+ year notebook exports stable.
- Avoid holding unnecessary page content in memory.
- Stream or process page-by-page where possible.
- Keep progress accurate and responsive.

Testing needs:

- Synthetic hierarchy with many notebooks, sections, and pages.
- Deep subpage trees.
- Many images/assets.
- Cancellation during a long export.

### 13. Path Length And Naming Controls

Priority: Medium

References:

- [v1.3.0 release: max page title length setting](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.4.0 release: path errors](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)

Current project context:

- This project already has robust Windows-safe path sanitization.
- It handles invalid characters, trailing spaces/periods, reserved names, and long path shortening.

Future improvements:

- Add optional max filename/component length controls if users hit deep hierarchy path limits.
- Keep generated shortening deterministic.
- Preserve readable names when path length allows.

### 14. Markdown Output Quality

Priority: Medium

References:

- [v0.5.0 release: line break behavior](https://github.com/alxnbl/onenote-md-exporter/releases/tag/0.5.0)
- [v1.2.0 release: cleaner line breaks](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.2.0)
- [markdownlint-cli](https://github.com/DavidAnson/markdownlint-cli)

Current project context:

- This project already bundles markdownlint-cli.
- Earlier work identified trailing newline and bare URL wrapping as important output-quality details.

Feature goals:

- Keep trailing newlines correct.
- Keep bare URLs lint-clean or intentionally configured.
- Avoid duplicate/strange blank lines.
- Keep Markdown readable without destroying intentional OneNote spacing.

### 15. Feature And Limitations Matrix

Priority: High documentation work

References:

- [alxnbl README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)
- [alxnbl Joplin migration comparison](https://github.com/alxnbl/onenote-md-exporter/blob/main/doc/migration-to-joplin.md)

Add a README table like this:

| OneNote feature | Current support | Planned improvement | Notes |
| --- | --- | --- | --- |
| Notebook hierarchy | Supported | Documentation examples | Folders |
| Section groups | Supported | Documentation examples | Nested folders |
| Pages/subpages | Supported | Document terminology | Uses `pageLevel` |
| Images | Supported | Asset organization modes | Relative links |
| File attachments | Partial/unknown | Export embedded files | Needs research/tests |
| OneNote dates | Not yet | File timestamps + YAML | Issue #2 |
| Internal links | Not yet | Markdown/wikilink conversion | Later feature |
| Tags/checklists | Partial/unknown | Markdown checkboxes/tags | Later feature |
| Folded content | Partial | Stronger preservation/warnings | Needs tests |
| Simple tables | Supported/partial | Verify | Needs tests |
| Complex tables | Partial | HTML fallback | Needs tests |
| Highlights/colors | Partial | Highlight/styling modes | Later feature |
| Handwriting/ink | Unsupported/partial | Document limitation | May not be practical |
| Protected sections | Requires unlock | Better warnings | User must unlock |

## Lower Priority Or Deferred Ideas

### Joplin Export Mode

References:

- [alxnbl Joplin migration guide](https://github.com/alxnbl/onenote-md-exporter/blob/main/doc/migration-to-joplin.md)
- [Joplin raw directory references in alxnbl code](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/JoplinExportService.cs)

This could be useful eventually, but it is a bigger product direction. It should not block making the generic Markdown exporter excellent.

### Markdown Flavor Modes

Possible future modes:

- GitHub-flavored Markdown.
- Strict/CommonMark-oriented Markdown.
- Wiki-link-oriented Markdown.
- HTML-preserving Markdown.

Recommendation:

- Add only when users have clear target-app needs.
- Avoid creating too many options before the core preservation work is reliable.

### Open Output Folder After Export

Small GUI convenience:

- Open the output folder after successful export.
- Possibly make this optional.

This is useful, but not urgent.

## Engineering Architecture Plan

### Shared Export Planning

Current pressure:

- GUI and CLI export traversal have similar but separate logic.
- Adding asset/date/link/layout modes risks divergence.

Recommendation:

- Add shared export planning helpers before adding many options.
- A planning object should know:
  - Output root.
  - Sanitized notebook path.
  - Sanitized section path.
  - Page Markdown path.
  - Page folder path for subpages.
  - Asset folder path for the selected asset mode.
  - Relative asset link prefix for the Markdown file.

Possible types:

```csharp
public sealed class PageExportContext
{
    public OneNoteItem Page { get; init; }
    public string MarkdownFilePath { get; init; }
    public string MarkdownFolderPath { get; init; }
    public string AssetsFolderPath { get; init; }
    public string RelativeAssetsPath { get; init; }
}
```

```csharp
public sealed class ExportPathPlanner
{
    public PageExportContext CreatePageContext(...);
}
```

### Date Handling Service

Add a focused helper for setting timestamps:

```csharp
public interface IFileTimestampService
{
    void ApplyTimestamps(string filePath, DateTime? created, DateTime? modified);
}
```

Reasons:

- Keeps Windows file timestamp behavior isolated.
- Makes tests easier.
- Allows soft failure handling in one place.

### Link Conversion Service

Add a service after path planning exists:

```csharp
public sealed class OneNoteLinkConversionService
{
    public void RegisterPage(string oneNotePageId, string markdownPath, string title);
    public string ConvertLinks(string markdown, OneNoteLinkMode mode);
}
```

The service needs the final planned Markdown paths before conversion.

## Code Areas

Core option model:

- [ExportOptions.cs](../OneNoteMarkdownExporter/Services/ExportOptions.cs)

Export traversal and planning:

- [ExportService.cs](../OneNoteMarkdownExporter/Services/ExportService.cs)
- [MainWindow.xaml.cs](../OneNoteMarkdownExporter/MainWindow.xaml.cs)
- [ExportSelectionHelper.cs](../OneNoteMarkdownExporter/Services/ExportSelectionHelper.cs)

GUI and CLI:

- [MainWindow.xaml](../OneNoteMarkdownExporter/MainWindow.xaml)
- [CliHandler.cs](../OneNoteMarkdownExporter/Services/CliHandler.cs)

Paths and assets:

- [AssetPathResolver.cs](../OneNoteMarkdownExporter/Services/AssetPathResolver.cs)
- [ExportPathSanitizer.cs](../OneNoteMarkdownExporter/Services/ExportPathSanitizer.cs)

OneNote model and metadata:

- [OneNoteItem.cs](../OneNoteMarkdownExporter/Models/OneNoteItem.cs)
- [OneNoteService.cs](../OneNoteMarkdownExporter/Services/OneNoteService.cs)

Markdown conversion:

- [OneNoteXmlToMarkdownConverter.cs](../OneNoteMarkdownExporter/Services/OneNoteXmlToMarkdownConverter.cs)

Failure reporting:

- [ExportFailureFormatter.cs](../OneNoteMarkdownExporter/Services/ExportFailureFormatter.cs)

Public documentation:

- [README.md](../README.md)

## Test Plan

General rule:

- Tests must use synthetic and generic notebook, section, page, subpage, asset, and attachment names.
- Never encode behavior specific to a real private notebook.

### Required Tests For Immediate Work

Asset organization:

- Centralized default assets path.
- Centralized custom absolute path.
- Centralized custom relative path.
- Existing file rejected as assets folder.
- Notebook-level assets.
- Section-level assets.
- Page-level assets.
- Correct relative links from pages at different depths.
- Re-export overwrites generated asset files.

Dates:

- Parse `dateTime` from hierarchy XML.
- Parse `lastModifiedTime` from hierarchy XML.
- Missing dates stay null.
- Invalid dates do not break hierarchy parsing.
- File timestamps are set after Markdown write/lint.
- YAML front matter appears only when enabled.

Subpages:

- Parent page with child page.
- Parent page with child and grandchild.
- Export only selected subpage while preserving parent folder context.
- Do not mutate UI selection state during export.

### Tests For Backlog Features

Links:

- Keep original OneNote links.
- Convert resolvable page link to relative Markdown link.
- Convert resolvable page link to wikilink.
- Remove unresolved links but keep display text.
- Cross-notebook unresolved link is logged or warned.

Tags:

- Incomplete checkbox.
- Completed checkbox.
- Important/question/reminder tags.
- Tags inside lists.

Attachments:

- Embedded PDF/file.
- Media attachment.
- Duplicate attachment names.
- Attachment links respect selected asset organization mode.

Tables/styling:

- Simple table.
- Complex table fallback.
- Image in table cell.
- Highlight conversion.

Reliability:

- One page failure does not stop export.
- Final summary contains failures and warnings.
- Startup COM exception returns a useful message.

Validation command:

```powershell
dotnet test .\OneNoteMarkdownExporter.Tests\OneNoteMarkdownExporter.Tests.csproj
```

Manual validation scenarios:

- Export a synthetic notebook with nested section groups, subpages, images, links, tags, collapsed content, duplicate names, and long/special paths.
- Re-export to the same output with overwrite enabled.
- Inspect links in a Markdown viewer.
- Inspect created/modified timestamps in Windows Explorer.
- Confirm failures are shown in the GUI Failures tab and CLI summary.

## Proposed Implementation Order

1. Add option types and defaults for asset organization and date preservation.
2. Add shared path planning for page Markdown paths and asset folders.
3. Implement asset organization modes in CLI export.
4. Wire asset organization modes into GUI export.
5. Add date parsing to the OneNote model/service.
6. Apply file timestamps after Markdown write/lint.
7. Add optional YAML front matter.
8. Update README with issue #1/#2 docs and examples.
9. Add feature/limitations matrix.
10. Add internal link conversion.
11. Add file/media attachment export.
12. Add tags/checklists/highlights preservation.
13. Harden folded content and complex tables.
14. Improve diagnostics, startup messages, and final reports.
15. Revisit larger target-app modes such as Joplin export.

## Proposed Milestones

### Milestone 1: Issue #1 And #2 Completion

Deliver:

- Asset organization modes.
- Date parsing.
- File timestamp preservation.
- Optional YAML front matter.
- README examples for assets, subpages, and dates.
- Tests for asset paths, date parsing, timestamps, and repeated export behavior.

### Milestone 2: Trust And Documentation

Deliver:

- Feature/limitations matrix.
- Better final export report.
- Expanded troubleshooting for OneNote COM, sync, locked sections, and missing content.
- Clear issue response language explaining what is supported.

### Milestone 3: Migration Preservation

Deliver:

- Embedded file attachments.
- Media attachments where OneNote exposes binary content.
- OneNote tag and checkbox translation.
- Highlight preservation.

### Milestone 4: Knowledge Graph Preservation

Deliver:

- Internal OneNote link conversion.
- Link mode options for Markdown links and wikilinks.
- Cross-selection link warnings.

### Milestone 5: Hardening For Large Legacy Notebooks

Deliver:

- Collapsed content hardening.
- Complex table and image-in-table tests.
- Optional max name length controls.
- Memory and progress improvements for very large exports.

## Release Note Themes

When these ship, release notes should be curated rather than only auto-generated.

Suggested release note groups:

- Export organization.
- Date preservation.
- Page/subpage hierarchy documentation.
- Reliability and diagnostics.
- Markdown preservation improvements.
- Known limitations.

Example for the immediate release:

```markdown
## Highlights

- Added asset organization modes: centralized, notebook, section, and page.
- Added OneNote date preservation as Windows file timestamps.
- Added optional YAML front matter for created/updated page metadata.
- Documented how OneNote pages, subpages, and sub-subpages export to folders.

## Notes

- Existing centralized asset behavior remains the default.
- Custom asset folder paths apply to centralized mode.
- YAML metadata is opt-in because it changes Markdown content.
```

## Deliberate Non-Goals For Now

- Do not add a Pandoc/Word dependency just because another exporter uses it.
- Do not require users to edit JSON settings by hand for major options.
- Do not change the default page/subpage layout until there is clear demand.
- Do not make Joplin/raw export part of the immediate issue #1/#2 work.
- Do not add notebook-specific logic or tests based on one user's real notebooks.

## Reference Links

### This Repository

- [Repository](https://github.com/segunak/one-note-to-markdown)
- [Issue #1: Move Assets Folder?](https://github.com/segunak/one-note-to-markdown/issues/1)
- [Issue #2: Pages to Folders and File Dates](https://github.com/segunak/one-note-to-markdown/issues/2)
- [Releases](https://github.com/segunak/one-note-to-markdown/releases)
- [README](../README.md)

### Comparable Exporter

- [alxnbl/onenote-md-exporter](https://github.com/alxnbl/onenote-md-exporter)
- [alxnbl releases](https://github.com/alxnbl/onenote-md-exporter/releases)
- [alxnbl README](https://github.com/alxnbl/onenote-md-exporter/blob/main/README.md)
- [alxnbl README feature matrix](https://github.com/alxnbl/onenote-md-exporter#features-and-limitations)
- [alxnbl Joplin migration guide](https://github.com/alxnbl/onenote-md-exporter/blob/main/doc/migration-to-joplin.md)

### Comparable Exporter Releases

- [v1.6.0: OneNote link conversion, tag translation, table image fix](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.6.0)
- [v1.5.0: media attachments, folded paragraphs, encoding, memory optimization](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.5.0)
- [v1.4.0: highlights, GUID attachment names, path fixes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.4.0)
- [v1.3.0: corrupted page isolation, execution report, max page title length](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.3.0)
- [v1.2.0: cleaner line breaks and Joplin hierarchy](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.2.0)
- [v1.1.0: page hierarchy and resource folder settings](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.1.0)
- [v1.0.0: YAML front matter and duplicate title fixes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v1.0.0)
- [v0.5.0: line break behavior and bundled Pandoc](https://github.com/alxnbl/onenote-md-exporter/releases/tag/0.5.0)
- [v0.4.0: command-line parameters and image references](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.4.0)
- [v0.3.1: temp folder fix](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.3.1)
- [v0.3: self-contained release](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.3)
- [v0.2.1: more logs and minor fixes](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.2.1)
- [v0.2: file attachments](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.2)
- [v0.1: initial prerelease](https://github.com/alxnbl/onenote-md-exporter/releases/tag/v0.1)

### Comparable Exporter Code References

- [ResourceFolderLocationEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/ResourceFolderLocationEnum.cs)
- [PageHierarchyEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/PageHierarchyEnum.cs)
- [OneNoteLinksHandlingEnum](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/OneNoteLinksHandlingEnum.cs)
- [OneNoteLinkTranslatorService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/OneNoteLinkTranslatorService.cs)
- [MdExportService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/MdExportService.cs)
- [ExportServiceBase](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/ExportServiceBase.cs)
- [AppSettings](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Infrastructure/AppSettings.cs)
- [TagsDefMap](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/TagsDefMap.cs)
- [JoplinExportService](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Services/Export/JoplinExportService.cs)
- [Attachment model](https://github.com/alxnbl/onenote-md-exporter/blob/main/src/OneNoteMdExporter/Models/Attachement.cs)

### Microsoft And Tooling References

- [Microsoft OneNote Application interface](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote)
- [OneNote GetHierarchy method](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote#gethierarchy-method)
- [OneNote GetPageContent method](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote#getpagecontent-method)
- [OneNote GetBinaryPageContent method](https://learn.microsoft.com/en-us/office/client-developer/onenote/application-interface-onenote#getbinarypagecontent-method)
- [OneNote desktop version guidance](https://support.microsoft.com/en-us/office/what-s-the-difference-between-the-onenote-versions-a624e692-b78b-4c09-b07f-46181958118f)
- [OneNote for Windows 10 support status](https://support.microsoft.com/en-us/office/what-is-happening-to-onenote-for-windows-10-2b453bfe-66bc-4ab2-9118-01e7eb54d2d6)
- [WPF overview](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/overview/)
- [COM interop in .NET](https://learn.microsoft.com/en-us/dotnet/standard/native-interop/cominterop)
- [markdownlint-cli](https://github.com/DavidAnson/markdownlint-cli)
- [System.CommandLine](https://github.com/dotnet/command-line-api)