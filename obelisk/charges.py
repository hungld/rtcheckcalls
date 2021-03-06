import time
from datetime import datetime

from obelisk.model import Model, User, Charge

def get_charges(user_ext):
	model = Model()
	user = model.get_user_fromext(user_ext)

	res = ""
	for charge in user.charges:
		date = charge.timestamp
		credit = charge.credit
		if charge.concept:
			concept = charge.concept
		else:
			concept = ''
		res += "<tr><td>%s</td><td>%s</td><td>%s</td></tr>\n" % (date, credit,concept)
	return res

def add_charge(user_ext, amount, concept=""):
	model = Model()
	user = model.get_user_fromext(user_ext)
	if not user:
		user = User(user_ext)
		model.session.add(user)

	if concept:
		charge = Charge(user=user, timestamp=datetime.now(), credit=amount, concept=concept)
	else:
		charge = Charge(user=user, timestamp=datetime.now(), credit=amount)
	model.session.add(charge)
	
	model.session.commit()

if __name__ == "__main__":
	print get_charges("816")
	add_charge("816", 2.0)
	print get_charges("816")
	add_charge("816", -2.0)
	print get_charges("816")
