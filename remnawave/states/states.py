from aiogram.fsm.state import State, StatesGroup

class RemnaUserStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_expiry = State()
    waiting_for_limit_gb = State()
    waiting_for_hwid = State()
    waiting_for_search_query = State()
    waiting_for_edit_gb = State()
    waiting_for_edit_hwid = State()
    waiting_for_extend_days = State()

class RemnaNodeStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_port = State()
    selecting_profile = State()
    waiting_for_edit_name = State()
    waiting_for_edit_address = State()
    waiting_for_edit_port = State()

class RemnaProfileStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_edit_name = State()

class RemnaHostStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_port = State()
    selecting_profile = State()
    selecting_inbound = State()
    waiting_for_edit_remark = State()
    waiting_for_edit_address = State()
    waiting_for_edit_port = State()
    waiting_for_edit_path = State()
    waiting_for_edit_sni = State()
    waiting_for_edit_host = State()
    waiting_for_edit_alpn = State()
    waiting_for_edit_fingerprint = State()

class RemnaPanelStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_html = State()
    waiting_for_edit_name = State()
    waiting_for_edit_html = State()
