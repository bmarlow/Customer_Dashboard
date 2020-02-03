import argparse
import getpass
import json
import requests
import sys
import concurrent.futures
import logging
import io
import os

parser = argparse.ArgumentParser()
parser.add_argument("-u", "--user", help="provide user name for https://access.redhat.com/", default="", required=True)
parser.add_argument("-p", "--password", help="password for the username provided, if you wish for it to be encrypted please leave blank and you will be prompted", default="")
parser.add_argument("-sd", "--startdate", help="provide the start date of the data you would like to review (YYYY-MM-DD format)", default="", required=True)
parser.add_argument("-ed", "--enddate", help="provide the end date of the data you would like to review (YYYY-MM-DD format)", default="", required=True)
parser.add_argument("-a", "--accountsearch", help="the account name you would like to search for", default="")
parser.add_argument("-i", "--include", help="include accounts that have 0 values", action="store_true", default=False)
parser.add_argument("-c", "--csvout", help="also send data to csv file in same dir as script", action="store_true", default=False)
parser.add_argument("-o", "--fileoutput", help="output filename for csv", default="customer-dashboard.csv")
parser.add_argument("-f", "--file", help="load account numbers from CSV file", default="")


args = parser.parse_args()
user = args.user
password = args.password
account_search = args.accountsearch
include = args.include
csv_out = args.csvout
csv_filename = args.fileoutput
file = args.file
start_date = args.startdate
end_date = args.enddate


def main():
    """main function, instantiates object for each account"""
    if file:
        accounts = get_accounts_from_csv(file)
    else:
        accounts = get_accounts(account_search)

    # create csv_output file and input column headers before threading
    if csv_out:
        # destroy previous csv file output
        file_destroy(csv_filename)

        # write column headers to csv file output
        file_write(csv_filename, "Account #,Account Name,Subscriptions,Active,ReadyToRenew,FutureDated,RecentlyExpired," + "Views,Knowledgebase,Product Pages,Discussions,Documentation,Errata,Security,Enhancement,Bug Fix," + "Cases,Severity 1,Severity 2,Severity 3,Severity 4,Closed\n")

    # if you need to debug comment out the futures loop and use this one
    #for account_number, account_name in accounts.items():
    #    account_run(account_number, account_name)

    print("Account data collection beginning, please be patient...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        fs = [executor.submit(account_run, account_number, account_name) for account_number, account_name in accounts.items()]
        concurrent.futures.wait(fs)

    print("Account Parsing Finished, a total of " + str(len(accounts)) + " accounts were checked.")


def account_run(account_number, account_name):
    """orchestrates the calling of other functions for calling"""
    # replace commas in account names so that csv output doesn't break
    account_name = account_name.replace(",", " ")

    account = CustomerDashboard(account_number, account_name)
    account.create_logger()

    # asynchronously make API calls
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
    views_async = executor.submit(account.get_views)
    errata_async = executor.submit(account.get_errata)
    cases_async = executor.submit(account.get_cases)
    labs_async = executor.submit(account.get_labs)
    subs_async = executor.submit(account.get_subs)

    # gather API call results
    views = views_async.result()
    errata = errata_async.result()
    cases = cases_async.result()
    labs = labs_async.result()
    subs = subs_async.result()

    # parse API results
    account.parse_views(views)
    account.parse_errata(errata)
    account.parse_cases(cases)
    account.parse_labs(labs)
    account.parse_subs(subs)

    account.close_logger()

    if csv_out:
        account.csv_account(account_name, account_number)
        account.csv_subs(subs)
        account.csv_views(views)
        account.csv_errata(errata)
        account.csv_cases(cases)
        file_write(csv_filename, "\n")


def get_accounts_from_csv(file):
    """generates a list of accounts from a csv file"""
    account_dict = {}
    with open(file) as f:
        account_numbers_list = f.readlines()

    account_numbers = account_numbers_list[0].split(",")

    for account_number in account_numbers:
        account_dict.update({account_number: "Import from CSV, No name Provided"})

    return account_dict


def get_accounts(account_search):
    """generate list of account numbers based on account name or account number"""
    account_dict = {}

    # different url used if an account number is provided
    if account_search.isnumeric():
        url = "https://access.redhat.com/hydra/rest/dashboard/v2/accounts?id="
    else:
        url = "https://access.redhat.com/hydra/rest/dashboard/v2/accounts?name="

    r = requests.get(url + account_search + "&limit=200", auth=(user, password))
    j = json.loads(r.text)

    # double check to make sure that the user authenticates successfully
    try:
        if j["message"] == "Unable to authenticate user":
            print("There was authentication error, please try again.")
            sys.exit(1)
    except KeyError:
        # if auth is successful keep going
        pass

    for i in j["accounts"]:
        account_name = (i["name"])
        account_number = (i["accountNumber"])
        if not None:
            account_dict.update({account_number: account_name})

    return account_dict


def file_destroy(filename):
    # destroy file e.g. previous csv output file
    if os.path.exists(filename):
        os.remove(filename)


def file_write(filename, data):
    # write string data to file (filename)
    with open(filename, 'a+') as f:
        f.write(data)


class CustomerDashboard(object):
    """object created for each account"""
    def __init__(self, account_number, account_name):
        self.account_number = account_number
        self.account_name = account_name
        self.base_url = "https://access.redhat.com/hydra/rest/dashboard/"
        self.logger = logging.getLogger(self.account_name + "-" + self.account_number)
        self.log_capture_string = io.StringIO()

    def create_logger(self):
        """creates logging object"""

        self.logger.setLevel(logging.INFO)

        buffer = logging.StreamHandler(self.log_capture_string)
        buffer.setFormatter(logging.Formatter("%(message)s"))
        self.logger.addHandler(buffer)
        self.logger.info("")
        self.logger.info("-------------------------------------------------------------------------------------")
        self.logger.info("-------------------------------------------------------------------------------------")
        self.logger.info("************ {:^45s}  ({:^10s}) ************".format(self.account_name, self.account_number))
        self.logger.info("-------------------------------------------------------------------------------------")
        self.logger.info("-------------------------------------------------------------------------------------")

    def close_logger(self):
        """prints and closes the logging object"""
        # grab the log stream from the stringio object
        log_contents = self.log_capture_string.getvalue()

        # close the stringio object if its only one run, because thats a nice thing to do
        self.log_capture_string.close()
        print(log_contents)

    def json_grabber(self, module):
        """utility for grabbing data"""
        r = requests.get(self.base_url + module + "?id=" + self.account_number + "&startDate=" + start_date + "&endDate=" + end_date, auth=(user, password))
        j = json.loads(r.text)
        return j

    def get_views(self):
        """get view data"""
        j = self.json_grabber("v2/views")
        return j

    def get_errata(self):
        """get errata data"""
        j = self.json_grabber("v2/errata")
        return j

    def get_cases(self):
        """get case data"""
        j = self.json_grabber("v2/cases")
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
        # special case for cases due to different structure of data
        # print all values, including zeros if include flag is set
        if include and dict_keys != ["cases"]:
            self.logger.info("")
            self.logger.info("-----------------------------------------------------------------")
            self.logger.info("******************* {:^25s} *******************".format(header))
            self.logger.info("-----------------------------------------------------------------")
            self.print_nested_dicts(data)

        elif dict_keys == ["cases"]:
            if data["total"] != 0:
                self.logger.info("")
                self.logger.info("-----------------------------------------------------------------")
                self.logger.info("******************* {:^25s} *******************".format(header))
                self.logger.info("-----------------------------------------------------------------")
                self.print_nested_dicts(data["overallSeverityTotal"])
            elif include:
                self.logger.info("")
                self.logger.info("-----------------------------------------------------------------")
                self.logger.info("******************* {:^25s} *******************".format(header))
                self.logger.info("-----------------------------------------------------------------")
                self.print_nested_dicts(data["overallSeverityTotal"])

        # if our filter is one level deep
        elif len(dict_keys) == 1:
            if data[dict_keys[0]] != 0:
                self.logger.info("")
                self.logger.info("-----------------------------------------------------------------")
                self.logger.info("******************* {:^25s} *******************".format(header))
                self.logger.info("-----------------------------------------------------------------")
                self.print_nested_dicts(data)

        # if our filter is two levels deep
        elif len(dict_keys) == 2:
            if data[dict_keys[0]][dict_keys[1]] != 0:
                self.logger.info("")
                self.logger.info("-----------------------------------------------------------------")
                self.logger.info("******************* {:^25s} *******************".format(header))
                self.logger.info("-----------------------------------------------------------------")
                self.print_nested_dicts(data)

        else:
            self.logger.info("")
            self.logger.info("-----------------------------------------------------------------")
            self.logger.info("******************* {:^25s} *******************".format(header))
            self.logger.info("-----------------------------------------------------------------")
            self.print_nested_dicts(data)

    def parse_views(self, view_data):
        """parse out content view data into something readable"""
        keys = ["grandTotal", "total"]
        header = "Content View Data"
        self.parser_print(keys, header, view_data)

    def parse_cases(self, case_data):
        """parse out case data into something readable"""
        keys = ["cases"]
        header = "Case Data"
        self.parser_print(keys, header, case_data)

    def parse_errata(self, errata_data):
        """parse out errata into something readable"""
        # doesn"t use parse_print or print_nested_dicts due to different data formatting

        # this is gross but there for consistent formatting
        if errata_data["grandTotal"] == 0:
            if include:
                self.logger.info("")
                self.logger.info("-----------------------------------------------------------------")
                self.logger.info("******************* {:^25s} *******************".format("Errata Data"))
                self.logger.info("-----------------------------------------------------------------")
                self.logger.info("  Critical: 0")
                self.logger.info("  Important: 0")
                self.logger.info("  Moderate: 0")
                self.logger.info("  Low: 0")
                self.logger.info("  Bugfix: 0")
                self.logger.info("  Security: 0")
                self.logger.info("  Enhancement: 0")
        # if no errata is consumed return from function
            return

        self.logger.info("")
        self.logger.info("-----------------------------------------------------------------")
        self.logger.info("******************* {:^25s} *******************".format("Errata Data"))
        self.logger.info("-----------------------------------------------------------------")
        self.logger.info("  Critical: " + str(errata_data["bySeverity"]["Critical"]))
        self.logger.info("  Important: " + str(errata_data["bySeverity"]["Important"]))
        self.logger.info("  Moderate: " + str(errata_data["bySeverity"]["Moderate"]))
        self.logger.info("  Low: " + str(errata_data["bySeverity"]["Low"]))
        self.logger.info("  Bugfix: " + str(errata_data["byType"]["bugfix"]))
        self.logger.info("  Security: " + str(errata_data["byType"]["security"]))
        self.logger.info("  Enhancement: " + str(errata_data["byType"]["enhancement"]))

    def parse_labs(self, labs_data):
        """parse out labs into something readable"""
        labs = {}
        # get a count of each of the used labs
        labs.update({"configuration": labs_data["configuration"]["labs"]})
        labs.update({"deployment": labs_data["deployment"]["labs"]})
        labs.update({"security": labs_data["security"]["labs"]})
        labs.update({"troubleshoot": labs_data["troubleshoot"]["labs"]})

        # doesn"t use parse_print or print_nested_dicts due to different data formatting
        for k, v in labs.items():
            # check if the value is an empty array
            if v != []:
                # if the header variable isn"t set then print it (so that it only executes on first dict item)
                try:
                    header
                except NameError:
                    self.logger.info("")
                    self.logger.info("-----------------------------------------------------------------")
                    self.logger.info("******************* {:^25s} *******************".format("Labs Data"))
                    self.logger.info("-----------------------------------------------------------------")
                    header = True
                self.logger.info("  " + k + ": " + str(len(v)))

    def parse_subs(self, subs_data):
        """parse out subs into something readable"""
        keys = ["active"]
        header = "Subscription Data"
        self.parser_print(keys, header, subs_data)

    def csv_account(self, account_name, account_number):
        # account details for csv
        file_write(csv_filename, account_number + "," + account_name + ",")

    def csv_subs(self, subs_data):
        # subscription details for csv
        total = subs_data["active"] + subs_data["readyToRenew"] + subs_data["futureDated"] + subs_data["recentlyExpired"]
        csv_data = (str(total) + "," + str(subs_data["active"]) + "," + str(subs_data["readyToRenew"]) + "," + str(subs_data["futureDated"]) + "," + str(subs_data["recentlyExpired"]) + ",")
        file_write(csv_filename, csv_data)

    def csv_views(self, view_data):
        # view details for csv
        csv_data = (str(view_data["grandTotal"]["total"]) + "," + str(view_data["grandTotal"]["Knowledgebase"]) + "," + str(view_data["grandTotal"]["Product Pages"]) + "," + str(view_data["grandTotal"]["Discussions"]) + "," + str(view_data["grandTotal"]["Documentation"]) + ",")
        file_write(csv_filename, csv_data)

    def csv_errata(self, errata_data):
        # errata details for csv
        csv_data = ("0,0,0,0,")
        if errata_data["grandTotal"] != 0:
            csv_data = (str(errata_data["grandTotal"]) + "," + str(errata_data["byType"]["security"]) + "," + str(errata_data["byType"]["enhancement"]) + "," + str(errata_data["byType"]["bugfix"]) + ",")
        file_write(csv_filename, csv_data)

    def csv_cases(self, case_data):
        # case details for csv
        csv_data = ("0,0,0,0,0,0")
        if case_data["total"] != 0:
            csv_data = (str(case_data["total"]) + "," + str(case_data["overallSeverityTotal"]["Severity 1"]) + "," + str(case_data["overallSeverityTotal"]["Severity 2"]) + "," + str(case_data["overallSeverityTotal"]["Severity 3"]) + "," + str(case_data["overallSeverityTotal"]["Severity 4"]) + "," + str(case_data["closed"]))
        file_write(csv_filename, csv_data)

    def print_nested_dicts(self, d):
        """utility for printing out nested dicts, hence the recursiveness"""
        for k, v in d.items():
            if isinstance(v, dict):
                self.logger.info("\n " + k)
                self.logger.info("  -------------------------------------------")
                self.print_nested_dicts(v)

            else:
                self.logger.info("  {:<15} : {:<10}".format(k, str(v)))


if __name__ == "__main__":
    if not file and not account_search:
        print("\nYou must select an account name/id or provide a CSV file with account numbers")
        sys.exit(1)

    if not password:
        password = getpass.getpass("\nEnter password for %s: " % user)
    main()
