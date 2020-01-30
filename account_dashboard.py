import argparse
import getpass
import json
import requests

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user", help="provide user name for https://access.redhat.com/", default="", required=True)
parser.add_argument("-p", "--password", help="password for the username provided, if you wish for it to be encrypted please leave blank and you will be prompted", default="")
parser.add_argument("-sd", "--startdate", help="provide the start date of the data you would like to review (YYYY-MM-DD format)", default="", required=True)
parser.add_argument("-ed", "--enddate", help="provide the end date of the data you would like to review (YYYY-MM-DD format)", default="", required=True)
parser.add_argument("-a", "--accountsearch", help="the account name you would like to search for", default="", required=True)
parser.add_argument("-i", "--include", help="include accounts that have 0 values", action="store_true", default=False)
parser.add_argument("-c", "--csv", help="also send data to csv file in same dir as script", action="store_true", default=False)


args = parser.parse_args()
user = args.user
password = args.password
account_search = args.accountsearch
include = args.include
csv = args.csv
start_date = args.startdate
end_date = args.enddate


def main():
    """main function, instantiates object for each account"""
    accounts = get_accounts(account_search)

    for account_number, account_name in accounts.items():
        account = CustomerDashboard(account_number, account_name)
        print('')
        print('-------------------------------------------------------------------------------------')
        print('-------------------------------------------------------------------------------------')
        print("*********************** {:^25s}  ({:^8s}) ***********************".format(account_name, account_number))
        print('-------------------------------------------------------------------------------------')
        print('-------------------------------------------------------------------------------------')
        views = account.get_views()
        errata = account.get_errata()
        cases = account.get_cases()
        labs = account.get_labs()
        subs = account.get_subs()
        account.parse_views(views)
        account.parse_errata(errata)
        account.parse_cases(cases)
        account.parse_labs(labs)
        account.parse_subs(subs)

        if csv:
            #csv instructions here
            pass


def get_accounts(account_search):
    """generate list of account numbers based on account name or account number"""
    account_dict = {}

    # different url used if an account number is provided
    if account_search.isnumeric():
        url = 'https://access.redhat.com/hydra/rest/dashboard/v2/accounts?id='
    else:
        url = 'https://access.redhat.com/hydra/rest/dashboard/v2/accounts?name='

    r = requests.get(url + account_search + '&limit=200', auth=(user, password))
    j = json.loads(r.text)
    for i in j["accounts"]:
        account_name = (i["name"])
        account_number = (i["accountNumber"])
        if not None:
            account_dict.update({account_number: account_name})

    return account_dict


class CustomerDashboard(object):
    """object created for each account"""
    def __init__(self, account_number, account_name):
        self.account_number = account_number
        self.account_name = account_name
        self.base_url = "https://access.redhat.com/hydra/rest/dashboard/"

    def json_grabber(self, module):
        """utility for grabbing data"""
        r = requests.get(self.base_url + module + "?id=" + self.account_number + "&startDate=" + start_date + "&endDate=" + end_date, auth=(user, password))
        j = json.loads(r.text)
        return j

    def get_views(self):
        """get view data"""
        j = self.json_grabber("v2/views")
        return j

    def get_cases(self):
        """get case data"""
        j = self.json_grabber("v2/cases")
        return j

    def get_errata(self):
        """get errata data"""
        j = self.json_grabber("v2/errata")
        return j

    def get_labs(self):
        """get labs data"""
        j = self.json_grabber("labs")
        return j

    def get_subs(self):
        """get subs data"""
        j = self.json_grabber("v2/subscriptions")
        return j

    def parser_print(self, dict_keys, header, data):
        """prints out the parsed data"""
        # print all values, including zeros if include flag is set
        if include:
            print('')
            print('-----------------------------------------------------------------')
            print("******************* {:^25s} *******************".format(header))
            print('-----------------------------------------------------------------')
            self.print_nested_dicts(data)

        # special case for cases due to different structure of data
        elif dict_keys == ['cases']:
            print('')
            print('-----------------------------------------------------------------')
            print("******************* {:^25s} *******************".format(header))
            print('-----------------------------------------------------------------')
            self.print_nested_dicts(data["overallSeverityTotal"])

        # if our filter is one level deep
        elif len(dict_keys) == 1:
            if data[dict_keys[0]] != 0:
                print('')
                print('-----------------------------------------------------------------')
                print("******************* {:^25s} *******************".format(header))
                print('-----------------------------------------------------------------')
                self.print_nested_dicts(data)

        # if our filter is two levels deep
        elif len(dict_keys) == 2:
            if data[dict_keys[0]][dict_keys[1]] != 0:
                print('')
                print('-----------------------------------------------------------------')
                print("******************* {:^25s} *******************".format(header))
                print('-----------------------------------------------------------------')
                self.print_nested_dicts(data)

        else:
            print(header)
            self.print_nested_dicts(data)

    def parse_views(self, view_data):
        """parse out content view data into something readable"""
        keys = ["grandTotal", "total"]
        header = 'Content View Data'
        self.parser_print(keys, header, view_data)

    def parse_cases(self, case_data):
        """parse out case data into something readable"""
        keys = ["cases"]
        header = "Case Data"
        self.parser_print(keys, header, case_data)

    def parse_errata(self, errata_data):
        """parse out errata into something readable"""
        # doesn't use parse_print or print_nested_dicts due to different data formatting
        print('')
        print('-----------------------------------------------------------------')
        print("******************* {:^25s} *******************".format("Errata Data"))
        print('-----------------------------------------------------------------')

        print("  Critical: " + str(errata_data["bySeverity"]["Critical"]))
        print("  Important: " + str(errata_data["bySeverity"]["Important"]))
        print("  Moderate: " + str(errata_data["bySeverity"]["Moderate"]))
        print("  Low: " + str(errata_data["bySeverity"]["Low"]))
        print("  Bugfix: " + str(errata_data["byType"]["bugfix"]))
        print("  Security: " + str(errata_data["byType"]["security"]))
        print("  Enhancement: " + str(errata_data["byType"]["enhancement"]))

    def parse_labs(self, labs_data):
        """parse out labs into something readable"""
        labs = {}
        # get a count of each of the used labs
        labs.update({'configuration': labs_data['configuration']['labs']})
        labs.update({'deployment': labs_data['deployment']['labs']})
        labs.update({'security': labs_data['security']['labs']})
        labs.update({'troubleshoot': labs_data['troubleshoot']['labs']})

        # doesn't use parse_print or print_nested_dicts due to different data formatting
        for k, v in labs.items():
            # check if the value is an empty array
            if v != []:
                # if the header variable isn't set then print it (so that it only executes on first dict item)
                try:
                    header
                except NameError:
                    print('')
                    print('-----------------------------------------------------------------')
                    print("******************* {:^25s} *******************".format("Labs Data"))
                    print('-----------------------------------------------------------------')
                    header = True
                print("  " + k + ": " + str(len(v)))

    def parse_subs(self, subs_data):
        """parse out subs into something readable"""
        keys = ["active"]
        header = "Subscription Data"
        self.parser_print(keys, header, subs_data)
        pass

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

    def csv_subs(self, subs_data):
        """generate csv output for subs_data"""
        pass

    def print_nested_dicts(self, d):
        """utility for printing out nested dicts, hence the recursiveness"""
        for k, v in d.items():
            if isinstance(v, dict):
                print('\n  ' + k)
                print('  -------------------------------------------')
                self.print_nested_dicts(v)
            else:
                print("  {:<15} : {:<10}".format(k, str(v)))


if __name__ == '__main__':
    if not password:
        password = getpass.getpass('\nEnter password for %s: ' % user)
    main()
