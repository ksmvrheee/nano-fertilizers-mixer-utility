from components.menu_bar import NavigationMenu
from config import *
from database import initialize_db
from routing import ROUTES

initialize_db()


def main(page: ft.Page):
    page.theme = ft.Theme(color_scheme_seed=COLOR_THEME_SEED)

    page.window.width = PAGE_BASIC_WIDTH
    page.window.height = PAGE_BASIC_HEIGHT

    page.window.min_width = PAGE_MIN_WIDTH
    page.window.min_height = PAGE_MIN_HEIGHT

    page.window.max_width = PAGE_MAX_WIDTH
    page.window.max_height = PAGE_MAX_HEIGHT

    page.title = f'Nano-fertilizers Mixer Utility v{VERSION}'

    content_container = ft.Container()
    current_page_object = None

    def on_navigate(route_name: str):
        """
        A function that changes the current displaying view.

        :param route_name: the name of the route to navigate to, should
            be a key in the app's ROUTES collection in the routing module.
        """
        nonlocal current_page_object  # storing the current displayable page object
        page_properties = ROUTES.get(route_name, False)

        page.overlay.clear()

        if not page_properties:
            current_page_object = None
            content_container.content = ft.Text('404: Page not found', weight=ft.FontWeight.BOLD,
                                                color=ft.colors.RED_ACCENT)
            page.update()
            return

        if current_page_object is not None and hasattr(current_page_object, 'ready_to_leave'):
            # checking if navigation is possible at the moment
            if not current_page_object.ready_to_leave:
                if hasattr(current_page_object, 'prevent_leaving'):
                    # executing actions for checking the unsubmitted user's input and preventing leaving the page
                    # also providing the way to leave the page if user is willing to abandon the unsubmitted input
                    current_page_object.prevent_leaving(navigate_to_leaving_destination=lambda: on_navigate(route_name))

                return  # leaving prevention

        if page_properties.get('takes_page_object', False):
            current_page_object = page_properties['page'](page)
        else:
            current_page_object = page_properties['page']()

        # constructing and updating the page layout
        content_container.content = current_page_object.build()
        page.update()

    # initial page layout
    page.add(
        ft.Column([
            ft.Container(NavigationMenu(on_navigate=on_navigate), margin=ft.margin.only(top=5)),
            ft.Container(ft.Divider(), margin=ft.margin.only(bottom=-10)),
            content_container
        ])
    )

    on_navigate('home')  # initial page view

ft.app(target=main)
