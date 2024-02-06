from RPLCD.i2c import CharLCD
import time
import threading
import subprocess

# Constants
MAIN_MENU, DIAL_NUMBER, CONTACTS, EMERGENCY, SETTINGS, SYSTEM, VIEW_HEART_RATE = range(7)
MENU_ITEMS = ['Dial', 'Contacts', 'Emergency', 'Heart Rate', 'Settings', 'System']
DIAL_CHARS = [str(i) for i in range(10)] + ['End']
CONTACT_CHARS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ") + ['End']
EMERGENCY_NUMBERS = ['911', '000']
AUTO_SCROLL_INTERVAL = 1  # Seconds between auto-scrolls
DEFAULT_CONTACTS = {'Mom': '1234567890', 'Dad': '0987654321', 'Doctor': '5555555555'}

# Initialize the LCD
lcd = CharLCD('PCF8574', 0x3F)

class CPI:
    def __init__(self):
        self.current_menu = MAIN_MENU
        self.menu_index = 0
        self.contacts = DEFAULT_CONTACTS.copy()
        self.in_pair_selection = False
        self.in_highlight_mode = False
        self.highlight_index = 0
        self.last_scroll = time.time()
        self.pause_scrolling = False
        self.keep_running = True
        self.auto_scroll_thread = threading.Thread(target=self.auto_scroll)
        self.auto_scroll_thread.daemon = True

    def auto_scroll(self):
        while self.keep_running:
            if not self.pause_scrolling and time.time() - self.last_scroll >= AUTO_SCROLL_INTERVAL:
                self.last_scroll = time.time()
                if self.current_menu == MAIN_MENU and not self.in_pair_selection:
                    self.menu_index = (self.menu_index + 2) % len(MENU_ITEMS)
                elif self.in_highlight_mode:
                    self.highlight_index = (self.highlight_index + 1) % 2
                self.display_menu()
            time.sleep(0.1)

    def display_menu(self):
        lcd.clear()
        if self.current_menu == MAIN_MENU and not self.in_pair_selection:
            items = MENU_ITEMS[self.menu_index:self.menu_index + 2]
            # Display the first item
            lcd.write_string(f' {items[0]}')
            # Display the second item directly below the first, if present
            if len(items) > 1:
                lcd.cursor_pos = (1, 1)
                lcd.write_string(f'{items[1]}')
        elif self.in_highlight_mode:
            items = MENU_ITEMS[self.menu_index:self.menu_index + 2]
            # Display items with highlighter for selection
            for i, item in enumerate(items):
                prefix = ">" if i == self.highlight_index else " "
                lcd.cursor_pos = (i, 0)
                lcd.write_string(f'{prefix} {item}')
    def select_option(self):
        if self.current_menu == MAIN_MENU:
            if not self.in_pair_selection:
                self.in_pair_selection = True
                self.in_highlight_mode = len(MENU_ITEMS[self.menu_index:self.menu_index + 2]) > 1
                self.highlight_index = 0
                self.display_menu()
            elif self.in_highlight_mode:
                selected_option = MENU_ITEMS[self.menu_index + self.highlight_index]
                self.access_menu_item(selected_option)

    def access_menu_item(self, selected_option):
        self.in_pair_selection = False
        self.in_highlight_mode = False
        if selected_option == 'Dial':
            self.dial_number()
        elif selected_option == 'Contacts':
            self.manage_contacts()
        elif selected_option == 'Emergency':
            self.dial_emergency_number()
        elif selected_option == 'Heart Rate':
            self.display_heart_rate()
        elif selected_option == 'Settings':
            self.adjust_settings()
        elif selected_option == 'System':
            self.system_actions()
        self.reset_menu_state()


    def dial_number(self):
        """Method to dial a number with interactive input."""
        self.input_string = ""  # Initialize the input string
        char_index = 0  # Start with the first character in DIAL_CHARS

        while True:
            lcd.clear()
            lcd.write_string(f"Enter Number:\n{self.input_string}{DIAL_CHARS[char_index]}")
            action = self.get_action()  # Implement this method to get the actual button press

            if action == 'single':
                if len(self.input_string) < 10:  # Check if the input string is less than 10 characters
                    self.input_string += DIAL_CHARS[char_index]
                    char_index = 0  # Reset char_index after selecting a character
                if len(self.input_string) == 10:  # Once 10 digits are entered, break from the loop
                    break
            elif action == 'double':
                self.input_string = self.input_string[:-1]  # Remove the last character
                char_index = 0  # Reset char_index after deleting a character
            elif action == 'long':
                self.input_string = ""  # Clear the entire input string
                char_index = 0  # Reset char_index after clearing input

            char_index = (char_index + 1) % len(DIAL_CHARS)  # Cycle through DIAL_CHARS
            time.sleep(0.3)  # Adjust the speed of character cycling

        # After finalizing the number, display the dialing message
        lcd.clear()
        lcd.write_string(f"Dialing:\n{self.input_string}")
        time.sleep(3)  # Simulate dialing duration
        self.return_to_main_menu()  # Implement method to return to the main menu

    def manage_contacts(self):
        # Logic to manage contacts
        contact_names = list(self.contacts.keys()) + ['Add Contact']
        selected_contact = self.select_from_options(contact_names, "Manage Contacts")
        if selected_contact == 'Add Contact':
            self.add_contact()
        else:
            self.edit_or_remove_contact(selected_contact)

    def edit_or_remove_contact(self, contact_name):
        # Logic to edit or remove a contact
        options = ['Edit', 'Remove']
        selected_option = self.select_from_options(options, f'{contact_name}')
        if selected_option == 'Edit':
            self.edit_contact(contact_name)
        elif selected_option == 'Remove':
            self.remove_contact(contact_name)

    def add_contact(self):
        # Logic to add a new contact
        name = self.collect_input(CONTACT_CHARS, "Enter Name", False)
        number = self.collect_input(DIAL_CHARS, "Enter Number", True)
        self.contacts[name] = number
        lcd.clear()
        lcd.write_string(f'Contact {name} added')
        time.sleep(2)

    def edit_contact(self, contact_name):
        # Logic to edit an existing contact
        new_name = self.collect_input(CONTACT_CHARS, "New Name", False)
        new_number = self.collect_input(DIAL_CHARS, "New Number", True)
        del self.contacts[contact_name]  # Remove old entry
        self.contacts[new_name or contact_name] = new_number
        lcd.clear()
        lcd.write_string(f'Contact edited')
        time.sleep(2)

    def remove_contact(self, contact_name):
        # Logic to remove a contact
        del self.contacts[contact_name]
        lcd.clear()
        lcd.write_string(f'Contact {contact_name} removed')
        time.sleep(2)

    def dial_emergency_number(self):
        # Logic to dial an emergency number
        selected_emergency_number = self.select_from_options(EMERGENCY_NUMBERS, "Emergency")
        lcd.clear()
        lcd.write_string(f'Dialing: {selected_emergency_number}')
        time.sleep(3)
        self.reset_menu_state()

    def display_heart_rate(self):
        # Logic to display heart rate (or lack thereof)
        lcd.clear()
        lcd.write_string('No HR Sensor')
        time.sleep(2)
        self.reset_menu_state()

    def adjust_settings(self):
        # Logic to adjust settings
        global AUTO_SCROLL_INTERVAL
        options = ['Scroll Speed', 'Backlight Brightness']
        selected_setting = self.select_from_options(options, 'Adjust Settings')

        if selected_setting == 'Scroll Speed':
            # Adjust scroll speed
            speed_options = ['Fast', 'Medium', 'Slow']
            selected_speed = self.select_from_options(speed_options, 'Scroll Speed')
            AUTO_SCROLL_INTERVAL = {'Fast': 0.5, 'Medium': 1, 'Slow': 2}[selected_speed]
            lcd.clear()
            lcd.write_string(f'Speed: {selected_speed}')
            time.sleep(2)

        elif selected_setting == 'Backlight Brightness':
            # Adjust backlight brightness (this is a placeholder)
            brightness_options = ['High', 'Medium', 'Low']
            selected_brightness = self.select_from_options(brightness_options, 'Backlight')
            lcd.clear()
            lcd.write_string(f'Brightness: {selected_brightness}')
            time.sleep(2)

        self.reset_menu_state()
    
    def collect_input(self, char_set, prompt, include_backspace):
        input_string = ""
        char_index = 0
        while True:
            lcd.clear()
            lcd.write_string(f'{prompt}\n{input_string}{char_set[char_index]}')
            action = self.simulate_button_press()
            if action == 'scroll':
                char_index = (char_index + 1) % len(char_set)
            elif action == 'single':
                if char_set[char_index] == 'End':
                    return input_string
                input_string += char_set[char_index]
            elif action == 'double' and include_backspace:
                input_string = input_string[:-1]  # Backspace functionality

    def select_from_options(self, options, prompt):
        # Function to select from given options
        option_index = 0
        while True:
            lcd.clear()
            lcd.write_string(f'{prompt}\n> {options[option_index]}')
            action = self.simulate_button_press()
            if action == 'scroll':
                option_index = (option_index + 1) % len(options)
            elif action == 'single':
                return options[option_index]

    def confirm_action(self, prompt):
        # Function to confirm an action
        confirm_options = ['Yes', 'No']
        selected_option = self.select_from_options(confirm_options, prompt)
        return selected_option == 'Yes'

    def reset_menu_state(self):
        self.in_pair_selection = False
        self.in_highlight_mode = False
        self.menu_index = 0
        self.current_menu = MAIN_MENU
        self.display_menu()

    def simulate_button_press(self):
        action = input("Enter action (s/d/l): ")
        return 'single' if action == 's' else 'double' if action == 'd' else 'long'

    def start(self):
        self.auto_scroll_thread.start()
        while self.keep_running:
            action = self.simulate_button_press()
            if action == 'single':
                self.select_option()
            elif action == 'double':
                self.reset_menu_state()
            time.sleep(0.1)

    def stop(self):
        self.keep_running = False
        self.auto_scroll_thread.join()

# Main execution
cpi_system = CPI()
try:
    cpi_system.start()
finally:
    cpi_system.stop()



