from gi.repository import Adw, Gtk, GLib#, Gio, Pango
from .host_info import HostInfo
from .app_row import AppRow
from .error_toast import ErrorToast
from .properties_page import PropertiesPage
from .status_box import StatusBox
from .filters_page import FiltersPage

@Gtk.Template(resource_path="/io/github/flattool/Warehouse/packages_page/packages_page.ui")
class PackagesPage(Adw.BreakpointBin):
    __gtype_name__ = 'PackagesPage'
    gtc = Gtk.Template.Child
    packages_bpt = gtc()
    packages_toast_overlay = gtc()
    stack = gtc()
    scrolled_window = gtc()
    sidebar_button = gtc()
    filter_button = gtc()
    refresh_button = gtc()
    search_bar = gtc()
    search_entry = gtc()
    packages_split = gtc()
    packages_list_box = gtc()
    select_button = gtc()
    packages_navpage = gtc()
    status_view = gtc()
    content_stack = gtc()

    # Referred to in the main window
    #    It is used to determine if a new page should be made or not
    #    This must be set to the created object from within the class's __init__ method
    instance = None

    def generate_list(self, *args):
        self.packages_list_box.remove_all()
        GLib.idle_add(lambda *_: self.filters_page.generate_list())
        first = True
        for package in HostInfo.flatpaks:
            row = None
            if first:
                row = AppRow(package, lambda *_: self.stack.set_visible_child(self.packages_split))
            else:
                row = AppRow(package)
            package.app_row = row
            row.masked_status_icon.set_visible(package.is_masked)
            row.pinned_status_icon.set_visible(package.is_pinned)
            row.eol_package_package_status_icon.set_visible(package.is_eol)
            row.check_button.set_visible(self.select_button.get_active())
            try:
                if not package.is_runtime:
                    row.eol_runtime_status_icon.set_visible(package.dependant_runtime.is_eol)
            except Exception as e:
                self.packages_toast_overlay.add_toast(ErrorToast(_("Error getting Flatpak '{}'").format(package.info["name"]), str(e)).toast)
            self.packages_list_box.append(row)

        first_row = self.packages_list_box.get_row_at_index(0)
        self.packages_list_box.select_row(first_row)
        self.properties_page.set_properties(first_row.package)
        self.scrolled_window.set_vadjustment(Gtk.Adjustment.new(0,0,0,0,0,0)) # Scroll list to top

    def row_select_handler(self, list_box, row):
        self.properties_page.set_properties(row.package)
        self.properties_page.nav_view.pop()
        self.packages_split.set_show_content(True)
        self.filter_button.set_active(False)

    def filter_func(self, row):
        search_text = self.search_entry.get_text().lower()
        title = row.get_title().lower()
        subtitle = row.get_subtitle().lower()
        if search_text in title or search_text in subtitle:
            return True

    def set_selection_mode(self, is_enabled):
        i = 0
        while row := self.packages_list_box.get_row_at_index(i):
            i += 1
            GLib.idle_add(row.check_button.set_active, False)
            GLib.idle_add(row.check_button.set_visible, is_enabled)

    def set_status(self, status_box):
        self.stack.set_visible_child(self.status_view)
        if self.status_view.get_content() == status_box:
            return
        self.status_view.set_content(status_box)

    def refresh_handler(self, *args):
        self.set_status(self.loading_status)
        HostInfo.get_flatpaks(callback=self.generate_list)

    def select_button_handler(self, button):
        self.set_selection_mode(button.get_active())

    def filter_button_handler(self, button):
        if button.get_active():
            self.content_stack.set_visible_child(self.filters_page)
            self.packages_split.set_show_content(True)
        else:
            self.content_stack.set_visible_child(self.properties_page)

    def filter_page_handler(self, *args):
        if self.packages_split.get_collapsed() and not self.packages_split.get_show_content():
            self.filter_button.set_active(False)

    def __init__(self, main_window, **kwargs):
        super().__init__(**kwargs)
        HostInfo.get_flatpaks(callback=self.generate_list)

        # Extra Object Creation
        self.main_window = main_window
        self.properties_page = PropertiesPage(main_window, self)
        self.filters_page = FiltersPage(main_window, self)
        self.loading_status = StatusBox(_("Fetching Packages"), _("This should only take a moment"))

        # Apply
        self.set_status(self.loading_status)
        self.packages_list_box.set_filter_func(self.filter_func)
        self.content_stack.add_child(self.properties_page)
        self.content_stack.add_child(self.filters_page)
        self.__class__.instance = self

        # Connections
        main_window.main_split.connect("notify::show-sidebar", lambda sidebar, *_: self.sidebar_button.set_visible(sidebar.get_collapsed() or not sidebar.get_show_sidebar()))
        main_window.main_split.connect("notify::collapsed", lambda sidebar, *_: self.sidebar_button.set_visible(sidebar.get_collapsed() or not sidebar.get_show_sidebar()))
        self.sidebar_button.connect("clicked", lambda *_: main_window.main_split.set_show_sidebar(True))

        self.search_entry.connect("search-changed", lambda *_: self.packages_list_box.invalidate_filter())
        self.search_bar.set_key_capture_widget(main_window)
        self.packages_list_box.connect("row-activated", self.row_select_handler)
        self.refresh_button.connect("clicked", self.refresh_handler)
        self.select_button.connect("clicked", self.select_button_handler)
        self.filter_button.connect("toggled", self.filter_button_handler)
        self.packages_split.connect("notify::show-content", self.filter_page_handler)
        self.packages_bpt.connect("apply", self.filter_page_handler)
        self.filter_button.set_active(True)