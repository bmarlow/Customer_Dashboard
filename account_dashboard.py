import requests, json, argparse, getpass

start_date = '2019-01-01'
end_date = '2019-12-31'

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user", help="provide user name for https://access.redhat.com/", default="")
parser.add_argument("-p", "--password", help="password for the username provided, if you wish for it to be encrypted please leave blank and you will be prompted", default="")
parser.add_argument("-sd", "--startdate", help="provide the start date of the data you would like to review (YYYY-MM-DD format)", default="")
parser.add_argument("-ed", "--enddate", help="provide the end date of the data you would like to review (YYYY-MM-DD format)", default="")
parser.add_argument("-a", "--accountname", help="the account name you would like to search for", default="")
parser.add_argument("-i", "--include", help="include accounts that have 0 values", action="store_true", default=False)

args = parser.parse_args()
user = args.user
password = args.password
account_name = args.accountname
include = args.include
#start_date = args.startdate
#end_date = args.enddate



def main():
    account_numbers = get_accounts(account_name)
    #this is another comment
    for account_number in account_numbers:
        account = CustomerDashboard(account_number)
        views = account.get_views()
        #updates = account.get_updates()
        #cases = account.get_cases()
        #labs = account.get_labs()

        account.parse_views(views)
        #account.parse_updates(updates)
        #account.parse_cases()
        #account.parse_labs()


def get_accounts(account_name):
    """generate list of account numbers based on account name"""
    account_numbers = []
    r = requests.get('https://access.redhat.com/hydra/rest/dashboard/v2/accounts?name=' + account_name + '&limit=200', auth=(user, password))
    j = json.loads(r.text)
    for i in j["accounts"]:
        account_number = (i["accountNumber"])
        if not None:
            account_numbers.append(account_number)
    return account_numbers


class CustomerDashboard(object):
    """object created for each account"""
    def __init__(self, account_number):
        self.account_number = account_number
        self.base_url = 'https://access.redhat.com/hydra/rest/dashboard/v2/'

    def json_grabber(self, module):
        """utility for grabbing data"""
        r = requests.get(self.base_url + module + '?id=' + self.account_number + '&startDate=' + start_date + '&endDate=' + end_date, auth=(user, password))
        j = json.loads(r.text)
        return j

    def get_views(self):
        """get view data"""
        j = self.json_grabber('views')
        return j

    def get_cases(self):
        """get case data"""
        j = self.json_grabber('cases')
        return j

    def get_errata(self):
        """get errata data"""
        j = self.json_grabber('errata')
        return j

    def get_labs(self):
        """get labs data"""
        j = self.json_grabber('labs')
        return j

    def get_subs(self):
        """get subs data"""
        j = self.json_grabber('subscriptions')
        return j

    def parse_views(self, view_data):
        """parse out content view data into something readable"""
        if include:
            print('\nAccount Number: ' + str(self.account_number))
            self.print_nested_dicts(view_data)

        else:
            if view_data['grandTotal']['total'] != 0:
                print('\nAccount Number: ' + str(self.account_number))
                self.print_nested_dicts(view_data)
        pass

    def parse_cases(self, case_data):
        """parse out case data into something readable"""
        pass

    def parse_errata(self):
        """parse out errata into something readable"""
        pass

    def parse_labs(self):
        """parse out labs into something readable"""
        pass

    def parse_subs(self):
        """parse out subs into something readable"""

    def csv_views(self, view_data):
        """generate csv output for view_data"""
        pass

    def csv_cases(self, case_data):
        """generate csv output for case_data"""
        pass

    def csv_errata(self, errata_data):
        """generate csv output for errata_data"""
        pass

    def csv_labs(self, labs_data):
        """generate csv output for labs_data"""
        pass


    def print_nested_dicts(self, d):
        """utility for printing out nested dicts, hence the recursiveness"""
        for k, v in d.items():
            if isinstance(v, dict):
                print('\n' + k)
                self.print_nested_dicts(v)
            else:
                print("{0} : {1}".format(k, v))



if __name__ == '__main__':
    if not password:
        password = getpass.getpass('\nEnter password for %s: ' % user)
    main()
