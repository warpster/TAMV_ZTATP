# TAMV_ZTATP
Combo repo
My modifid version of DuetWedAPI.py and TAMV_GUI.py.
DuetWebAPI.py includes a new function
def getModelQuery(self,key):    # key is a list of the item paths for the sub section to be returned 

TAMVZTATP_GUI.py is TAMV_GUI.py modified so that when setting the command point, if it sees the Knob probe (configured as probe K3) and it is not triggered, 
it will use it to align the Z offset for the tools after it aligns the X and Y offsets and then moves on to the next tool.
