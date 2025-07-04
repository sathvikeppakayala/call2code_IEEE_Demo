def get_config(category):
    if category == 'phone':
        return {
            'to_email': 'kumarshiva02877@gmail.com',
            'subject': '91CRPC Request for Phone Number'
        }
    elif category == 'account':
        return {
            'to_email': 'eppakayalasathvik72@gmail.com',
            'subject': 'Request for Account Holder Details and Transaction History – Suspected Involvement in Online Scam Activity (U/s 91 CrPC)'
        }
    elif category == 'gateway':
        return {
            'to_email': 'gopal.reddy@innodatatics.com',
            'subject': 'Request for Merchant and Transaction Details – Suspected Online Scam Activity – U/s 91 CrPC'
        }
    elif category == 'meta':
        return {
            'to_email': 'kumarshiva02877@gmail.com',
            'subject': 'Request for Social Media Account Details and Login Metadata – Section 91 CrPC & 69(A) IT Act'
        }
    else:
        raise ValueError("Unknown category")
