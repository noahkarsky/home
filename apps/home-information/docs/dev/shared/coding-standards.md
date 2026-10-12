# Coding Standards

## Code Conventions Checklist

Checklists for writing and reviewing code.

**General**:
- [ ] Code does not use hard-coded "magic" strings.
- [ ] Code does no use any hard-coded "magic" numbers.
- [ ] All comments add value and follow our commenting guidelines.
- [ ] No urls appear as hard-coded path and all use Django url names and `reverse()`.
- [ ] There no .flake8 linting violations.
- [ ] The file ends with a newline
- [ ] All new files follow the project structure's name and location conventions.
- [ ] There are no Emoji's in any code, templates or documentation.
- [ ] All comments and docstrings use ASCII only (no em/en dashes, smart quotes, arrows, degree symbols, ellipses, etc.).

**Imports**:
- [ ] All module imports are at the top of the file.
- [ ] Imports are grouped logically: system/pip, django, project, apps then module local.
- [ ] Imports have one line space between groups.
- [ ] Within a group, imports are sorted alphabetically
- [ ] No module relies on indirect (hidden) imports
- [ ] There are no unused imports

**Method Declarations**:
- [ ] All methods uses type hints for their parameters and return values.
- [ ] All method definition with more than two arguments use one line per argunment.
- [ ] All multi-line method signatures have all their types and default values aligned.
- [ ] No methods return position-dependent tuples.

**Class Declarations**:
- [ ] All dataclass definitions have all their types and default values aligned.
- [ ] All enum definitions have all their types and default values aligned.
- [ ] Are enums subclass LabeledEnum

**Method Calling**:
- [ ] All method calls use named parameters.
- [ ] All metghod calls with more than two argumants use one line per argument.
- [ ] All multi-line method calls use a comma after last item.
- [ ] Spaces surrounding all equals ("=") signs when passing parameters to methods.

**Expressions**:
- [ ] All boolean assignments to conditional clauses are wrapped in `bool()`.
- [ ] All loops end with an explicit  `continue` or a `return`.
- [ ] All methods end with an explicit `return` or a `raise`?
- [ ] All multi-line arrays, sets, dictionaries use a comma after last item.
- [ ] Compound/complex conditional statements use explicit delimiting parentheses.
- [ ] Single quote are used for all strings in Python code.
- [ ] All multi-line arrays, dictionaries and sets use a comma after last item.

**Views**:
- [ ] All url paths components follow our standard ordering conventions.
- [ ] All url Django names follow our standard naming conventions
- [ ] All view names match url names (except for casing and underlining).
- [ ] ALl views raise exceptions for common error conditions. (Let middleware handle it.)

**Templates**:
- [ ] Template names referenced in views closely match the view names that use them.
- [ ] No templates have in-line Javascript.
- [ ] No templates have in-line CSS.
- [ ] Templates appear in a subdirectory matching their purpose: modals, panes, pages.
- [ ] Template tags `load` statments near the top of the file.
- [ ] Django template comments use `{# #}` (single line) or `{% comment %}...{% endcomment %}` (multi-line), never `<!-- -->` (HTML comments ship to the browser).

## Code Conventions Details

### No "magic" strings

We do not use "magic" or hard-coded strings when needing multiple references. Any string that need to be used in two or more places is a risk of them being mismatched. This includes, but is not limited to:

All DOM ids and class strings that are shared between client and server must adhere to our `DIVID` pattern. See "Client-Server Namespace Sharing" in [Front End Guidelines](../frontend/frontend-guidelines.md).

### Type Hints

- We add type hints to dataclass fields, method parameters and method return values.
- We do not add type hints to locally declared method variables.
- Some allowed, but not required exceptions:
  - The `request` parameter when appearing in a Django view class.
  - Single parameter methods where the method name or parameter name makes its type unambiguous.

### Method Parameter Formatting

For readability, besides adding type hints to method parameters, we adhere to the following formatting conventions:
- For methods with a single parameter, or parameters of native types, they can appear in one line with the method name.
- If more than one parameter and app-defined types, then use a multiple line declaration.
- For methods with three or more parameters, we use one line per parameter and align the type names.

**Good Examples**:

```
    def set_entity( self, entity_id : int ) -> EntityPath:

    def set_entity_order( self, entity_id : int, rank : int ) -> EntityPath:

    def set_entity_path( self,
                         entity_id     : int,
                         location      : Location,
                         svg_path_str  : str        ) -> EntityPath:
```

**Bad Examples**:

```
    def set_entity_type( self, entity_id : int, entity_type : EntityType ) -> EntityPath:

    def set_entity_path( self,
                         entity_id : int,
                         location : Location,
                         svg_path_str: str ) -> EntityPath:

    def set_entity_path( self, entity_id : int,
                         location : Location, svg_path_str: str ) -> EntityPath:
```

### Variable Assignment vs Inlining

We prefer explicit variable assignment over inlining function calls. This is not about minimizing lines of code - it's about readability and debuggability.

**Good** - Named intermediate values
```python
table_name = self.queryset.model._meta.db_table
logger.debug( f"Processing table: {table_name}" )

cutoff_date = datetimeproxy.now() - timedelta( days=30 )
old_records = queryset.filter( created__lt=cutoff_date )
```

**Bad** - Inlined function calls
```python
logger.debug( f"Processing table: {self.queryset.model._meta.db_table}" )

old_records = queryset.filter(
    created__lt=datetimeproxy.now() - timedelta( days=30 )
)
```

Benefits of variable assignment:
- Provides semantic naming that clarifies intent
- Easier to debug (can inspect intermediate values)
- Improves readability by breaking complex expressions
- Allows reuse without recalculation

### Explicit Booleans

We prefer to wrap all expression that evaluate to a boolean in `bool()` to make it explicit what type we are expecting:

**Good**
```
   my_variable = bool( len(my_list) > 4 )
```

**Bad***
```
   my_variable = len(my_list) == 4
```

### Complex Boolean Expressions

- For boolean clauses and conditionals where there are multiple clauses, we prefer to explicitly enclose each clause with parentheses in order to make the intention clear.
- We do not rely on the user having a deep understanding of the compiler's ordeer of precedence.
- We use one line per clause unless the combined clauses are very short and obvious.
- Single boolean typed variables or methods that return a boolean do not need paretheses.

**Good**:
```
    if is_editing and location_view:
        pass
                
    if (( hass_state.domain == HassApi.SWITCH_DOMAIN )
          and ( HassApi.LIGHT_DOMAIN in prefixes_seen )):
        pass
                
    if ( HassApi.BINARY_SENSOR_DOMAIN in domain_set
         and device_class_set.intersection( HassApi.OPEN_CLOSE_DEVICE_CLASS_SET )):
        pass

   
```

**Bad**:
```
    if hass_state.domain == HassApi.SWITCH_DOMAIN and HassApi.LIGHT_DOMAIN == 'foo':
        pass
```

### Control Flow Statements
- Always include explicit `continue` statements in loops
- Always include explicit `return` statements in functions
- This improves code readability and makes control flow intentions explicit

Example:
```python
def process_items(items):
    results = []
    for item in items:
        if not item.valid:
            continue  # Explicit continue for invalid items
        
        if item.needs_processing:
            result = process(item)
            results.append(result)
            continue  # Explicit continue after processing
        
        # Handle non-processing case
        results.append(item.default_value)
        continue  # Explicit continue at end of loop
    
    return results  # Explicit return at end of function
```

### Operator Spacing
- Use spaces around assignment operators and most other operators in expressions
- Examples: `x = y + z`, `result += value`, `if count == 0`
- Exception: Don't add spaces in function keyword arguments (`func(x=y)`) or type annotations

### Parentheses Spacing (Deliberate PEP8 Deviation)
- **We prefer spaces inside parentheses for enhanced readability**
- This is a deliberate deviation from PEP8 standards (E201, E202)
- Examples:
  - Good: `if ( condition ):`
  - Good: `my_function( param1, param2 )`
  - Good: `result = calculate( x + y )`
- This applies to all parentheses: function calls, conditionals, expressions
- Rationale: Extra spacing improves readability by visually separating content from delimiters

### Boolean Expressions
When assigning or returning boolean values, wrap expressions in `bool()` to make intent explicit:

```python
# Good - explicit boolean conversion
is_active = bool(user.last_login)
in_modal_context = bool(request.POST.get('context') == 'modal')

# Avoid - implicit boolean conversion
is_active = user.last_login
in_modal_context = request.POST.get('context') == 'modal'
```

### Linting: Flake8 Configurations

The project uses two different flake8 configurations:
- Development Configuration (`src/.flake8`) : Our preferred style for daily development work, with specific whitespace deviations from PEP8 for enhanced readability:
  - **E201, E202**: We use spaces inside parentheses for better visual separation
  - **E221**: We align operators and values in multi-line declarations
  - **E251**: We use spaces around keyword parameters for consistency
  - **Note**: These are deliberate choices for improved code readability, not oversights
- CI Configuration (`src/.flake8-ci`): GitHub Actions enforces these standards and blocks PR merging if violations exist.

### ASCII-Only in Comments and Docstrings

Comments and docstrings use ASCII only. The benefits of visually-precise Unicode characters (em dashes, arrows, degree symbols) are outweighed by the costs: inconsistent rendering across terminals / diff viewers / editor configs; broken `grep` for anyone typing the ASCII equivalent; copy-paste mismatches between source and rendered docs; and visual ambiguity between similar-looking characters.

Common substitutions:

| Unicode | ASCII |
|---------|-------|
| `—` (em dash), `–` (en dash) | `--` or `-` |
| `→` (right arrow), `↔` (left-right arrow) | `->` or `and` |
| `…` (horizontal ellipsis) | `...` |
| `×` (multiplication sign) | `x` |
| `°` (degree symbol) | drop or restructure (e.g., `88F` instead of `88°F`) |
| `"` `"` (smart quotes), `'` `'` (smart apostrophes) | `"` `'` |

This is a syntactic concern (analogous to the no-emoji rule above) and is enforced by the comment-cleanup pass during its run.

Scope: applies to comments and docstrings. Does **not** apply to user-facing strings (`help_text`, `verbose_name`, error messages, log messages) — those follow their own UI / operator-copy conventions and may contain whatever characters their audience needs.

## Commenting

The content and semantics of comments — what to keep, rewrite, or remove — are covered in [Commenting Guidelines](commenting-guidelines.md). The checklist above covers the syntactic surface only.

### Special Cases

#### TRACE Pattern (Accepted)
- `TRACE = False # for debugging` is an accepted pattern
- Addresses Python logging limitation (lacks TRACE level below DEBUG)

## Related Documentation
- Commenting content and semantics: [Commenting Guidelines](commenting-guidelines.md)
- Testing standards: [Testing Guidelines](../testing/testing-guidelines.md)
- Backend patterns: [Backend Guidelines](../backend/backend-guidelines.md)
- Frontend standards: [Frontend Guidelines](../frontend/frontend-guidelines.md)
- Workflow and commits: [Workflow Guidelines](../workflow/workflow-guidelines.md)



