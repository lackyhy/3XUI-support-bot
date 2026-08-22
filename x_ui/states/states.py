from aiogram.fsm.state import State, StatesGroup

class PanelSetupStates(StatesGroup):
    waiting_for_panel_type = State()
    waiting_for_name = State()
    waiting_for_host = State()
    waiting_for_auth_type = State()
    waiting_for_token = State()
    waiting_for_username = State()
    waiting_for_password = State()

class RenamePanelStates(StatesGroup):
    waiting_for_new_name = State()

class AddClientStates(StatesGroup):
    selecting_inbound = State()
    waiting_for_email = State()
    waiting_for_limit_gb = State()
    waiting_for_expiry_days = State()
    waiting_for_limit_ip = State()
    waiting_for_initial_status = State()

class EditClientStates(StatesGroup):
    selecting_action = State()
    waiting_for_value = State()

class EditClientGBStates(StatesGroup):
    waiting_for_gb = State()

class EditClientExpiryStates(StatesGroup):
    waiting_for_days = State()

class SearchClientStates(StatesGroup):
    waiting_for_query = State()

class SetSubPortStates(StatesGroup):
    waiting_for_sub_port = State()

class ImportCredentialsStates(StatesGroup):
    waiting_for_key = State()
