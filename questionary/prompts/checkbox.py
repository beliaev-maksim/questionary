# -*- coding: utf-8 -*-

from typing import Any, Dict, List, Optional, Text, Union

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style, merge_styles
from prompt_toolkit.formatted_text import FormattedText

from questionary.constants import DEFAULT_QUESTION_PREFIX, DEFAULT_STYLE
from questionary.prompts import common
from questionary.prompts.common import Choice, InquirerControl, Separator
from questionary.question import Question


def checkbox(
    message: Text,
    choices: List[Union[Text, Choice, Dict[Text, Any]]],
    default: Optional[Text] = None,
    validate: Any = lambda a: True,
    qmark: Text = DEFAULT_QUESTION_PREFIX,
    style: Optional[Style] = None,
    use_pointer: bool = True,
    **kwargs: Any
) -> Question:
    """Ask the user to select from a list of items.

    This is a multiselect, the user can choose one, none or many of the
    items.

    Args:
        message: Question text

        choices: Items shown in the selection, this can contain `Choice` or
                 or `Separator` objects or simple items as strings. Passing
                 `Choice` objects, allows you to configure the item more
                 (e.g. preselecting it or disabeling it).

        default: Default return value (single value). If you want to preselect
                 multiple items, use `Choice("foo", checked=True)` instead.

        validate: Require the entered value to pass a validation. The
                  value can not be submited until the validator accepts
                  it (e.g. to check minimum password length).

                  This should be a function accepting the input and
                  returning a boolean. An optional second return value
                  is the error message to display.

        qmark: Question prefix displayed in front of the question.
               By default this is a `?`

        style: A custom color and style for the question parts. You can
               configure colors as well as font types for different elements.

        use_pointer: Flag to enable the pointer in front of the currently
                     highlighted element.

    Returns:
        Question: Question instance, ready to be prompted (using `.ask()`).
    """

    merged_style = merge_styles(
        [
            DEFAULT_STYLE,
            # Disable the default inverted colours bottom-toolbar behaviour (for
            # the error message). However it can be re-enabled with a custom
            # style.
            Style([("bottom-toolbar", "noreverse")]),
            style,
        ]
    )

    if not callable(validate):
        raise ValueError("validate must be callable")

    ic = InquirerControl(choices, default, use_pointer=use_pointer)

    def get_prompt_tokens():
        tokens = []

        tokens.append(("class:qmark", qmark))
        tokens.append(("class:question", " {} ".format(message)))

        if ic.is_answered:
            nbr_selected = len(ic.selected_options)
            if nbr_selected == 0:
                tokens.append(("class:answer", " done"))
            elif nbr_selected == 1:
                if isinstance(ic.get_selected_values()[0].title, list):
                    tokens.append(
                        (
                            "class:answer",
                            "".join(
                                [
                                    token[1]
                                    for token in ic.get_selected_values()[0].title
                                ]
                            ),
                        )
                    )
                else:
                    tokens.append(
                        (
                            "class:answer",
                            " [{}]".format(ic.get_selected_values()[0].title),
                        )
                    )
            else:
                tokens.append(
                    ("class:answer", " done ({} selections)".format(nbr_selected))
                )
        else:
            tokens.append(
                (
                    "class:instruction",
                    " (Use arrow keys to move, "
                    "<space> to select, "
                    "<a> to toggle, "
                    "<i> to invert)",
                )
            )
        return tokens

    def get_selected_values():
        return [c.value for c in ic.get_selected_values()]

    def perform_validation(selected_values):

        verdict = validate(selected_values)

        if isinstance(verdict, bool):
            valid = verdict
            error_message = FormattedText(
                [("class:validation-toolbar", "Invalid selection")]
            )
        else:
            valid, error_message = verdict

            if isinstance(error_message, str):
                error_message = FormattedText(
                    [("class:validation-toolbar", error_message)]
                )

        ic.error_message = (
            error_message if not valid and ic.submission_attempted else None
        )

        return valid

    layout = common.create_inquirer_layout(ic, get_prompt_tokens, **kwargs)

    bindings = KeyBindings()

    @bindings.add(Keys.ControlQ, eager=True)
    @bindings.add(Keys.ControlC, eager=True)
    def _(event):
        event.app.exit(exception=KeyboardInterrupt, style="class:aborting")

    @bindings.add(" ", eager=True)
    def toggle(event):
        pointed_choice = ic.get_pointed_at().value
        if pointed_choice in ic.selected_options:
            ic.selected_options.remove(pointed_choice)
        else:
            ic.selected_options.append(pointed_choice)

        perform_validation(get_selected_values())

    @bindings.add("i", eager=True)
    def invert(event):
        inverted_selection = [
            c.value
            for c in ic.choices
            if not isinstance(c, Separator)
            and c.value not in ic.selected_options
            and not c.disabled
        ]
        ic.selected_options = inverted_selection

        perform_validation(get_selected_values())

    @bindings.add("a", eager=True)
    def all(event):
        all_selected = True  # all choices have been selected
        for c in ic.choices:
            if (
                not isinstance(c, Separator)
                and c.value not in ic.selected_options
                and not c.disabled
            ):
                # add missing ones
                ic.selected_options.append(c.value)
                all_selected = False
        if all_selected:
            ic.selected_options = []

        perform_validation(get_selected_values())

    @bindings.add(Keys.Down, eager=True)
    @bindings.add("j", eager=True)
    def move_cursor_down(event):
        ic.select_next()
        while not ic.is_selection_valid():
            ic.select_next()

    @bindings.add(Keys.Up, eager=True)
    @bindings.add("k", eager=True)
    def move_cursor_up(event):
        ic.select_previous()
        while not ic.is_selection_valid():
            ic.select_previous()

    @bindings.add(Keys.ControlM, eager=True)
    def set_answer(event):

        selected_values = get_selected_values()
        ic.submission_attempted = True

        if perform_validation(selected_values):
            ic.is_answered = True
            event.app.exit(result=selected_values)

    @bindings.add(Keys.Any)
    def other(event):
        """Disallow inserting other text. """
        pass

    return Question(
        Application(layout=layout, key_bindings=bindings, style=merged_style, **kwargs)
    )
