import csv
import datetime as dt
import json
import operator
from pathlib import Path


RAW_DATA = Path(__file__).parent / "tickets.csv"
JSON_REPORT = Path(__file__).parent / f"report_{dt.datetime.now()}.json"
CSV_REPORT = Path(__file__).parent / "longtime_report.csv"

FIELDNAMES_CSV_REPORT = ["writing date", "open tickets", "lately closed tickets", "average time open"]

class TicketAnalyzer:

    def __init__(self):
        self.all_data = []
        self.imported_ids = []

    def load_data_from_file(self, filepath=RAW_DATA, data_type="tickets"):
        all_lines = []
        error_list = []
        row_counter = 1
        if not filepath.exists():
            print("Error: File has not been found! ")
            return False
        with open(filepath, "r", encoding="utf-8", newline="") as raw_data_file:
            for ticket in csv.DictReader(raw_data_file):
                row_counter += 1
                if data_type == "tickets": 
                    data_check = self.data_check_input_csv(ticket, data_type="tickets")
                elif data_type == "report":
                    data_check = self.data_check_input_csv(ticket, data_type="report")
                if data_check[1] is True:
                    all_lines.append(ticket)
                else:
                    error_list.append({row_counter: (data_check[0], data_check[2])})
        return [all_lines, error_list]


    def data_check_input_csv(self, ticket:dict, data_type="tickets"):
        if None in ticket.values():
            return [ticket, False, "row does not match expected format"]
        if data_type == "tickets":
            if ticket["ticket_id"] in self.imported_ids:
                return [ticket["ticket_id"], False, "ID is used multiple times"]
            try:
                ticket["eroeffnet"] = dt.datetime.strptime(ticket["eroeffnet"], "%Y-%m-%d %H:%M")
            except ValueError:
                return [ticket["ticket_id"], False, "date does not match expected format"]
            try:
                ticket["geschlossen"] = dt.datetime.strptime(ticket["geschlossen"], "%Y-%m-%d %H:%M")
            except ValueError:
                if ticket["geschlossen"] == "":
                    pass
            self.imported_ids.append(ticket["ticket_id"])
        return [ticket, True]

    def write_data_to_csv(self, data_to_write:dict,filepath=CSV_REPORT):
        if not filepath.exists():
            with open(CSV_REPORT, "w", newline="", encoding="utf-8") as csv_report_file:
                writer = csv.DictWriter(csv_report_file, FIELDNAMES_CSV_REPORT)
                writer.writeheader()
            print("Error: csv report file not found, created new one")
        with open(CSV_REPORT, "a", encoding="utf-8", newline="") as csv_report_file:
            writer = csv.DictWriter(csv_report_file, FIELDNAMES_CSV_REPORT)
            writer.writerow(data_to_write)

    def write_data_to_json(self, data_to_write:dict, filepath=JSON_REPORT):
        if filepath.exists():
            ask_overwrite = input("Error: Report does already exist! Do you want to overwrite? y/n")
            if ask_overwrite == "y":
                continue
            else:
                return
            

    def calculate_working_time(self, dataset=None, return_dict=False):
        if dataset is None:
            dataset = self.filter_data_condition(["geschlossen", "", "!="])
        dict_time_open = {k["ticket_id"]: self.calculate_open_time(k) for k in dataset}
        avg_worktime = sum(dict_time_open.values()) / len(dict_time_open)
        if return_dict is True:
            return dict_time_open
        return avg_worktime

    def calculate_open_time(self, ticket):
        try:
            time_opened = ticket["eroeffnet"]
            time_closed = ticket["geschlossen"]
            delta = (time_closed - time_opened)
            delta = float(delta.total_seconds() / 3600)
            if delta < 0:
                # print(f"Error: ticket with ID {ticket["ticket_id"]} was closed before creation")
                return 0
            return delta
        except ValueError:
            # print(f"Error: the ticket with ID {ticket["ticket_id"]} has a unregular date format")
            return 0

    def filter_data_condition(self, conditions, data_to_filter=None):
        results = []
        operators = {"==": operator.eq, "!=": operator.ne, "<": operator.lt, ">": operator.gt}
        if data_to_filter is None:
            data_to_filter = self.all_data
        for ticket in data_to_filter:
            if type(conditions[0]) is str:
                try:
                    if operators[conditions[2]](ticket[conditions[0]].lower(), conditions[1].lower()):
                        results.append(ticket)
                except KeyError:
                    print(f"Error: key {conditions[0]} does not exist in database")
                    break
                except AttributeError:
                    try: 
                        if operators[conditions[2]](ticket[conditions[0]], conditions[1]):
                            results.append(ticket)
                    except TypeError:
                        if operators[conditions[2]](dt.datetime.now(), conditions[1]):
                            results.append(ticket)
            elif type(conditions[0]) is list:
                for condition in conditions:
                    try:
                        if operators[condition[2]](ticket[condition[0]].lower(), condition[1].lower()):
                            continue
                        else:
                            break
                    except KeyError:
                        print(f"Error: key {conditions[0]} does not exist in database")
                        break
                    except AttributeError:
                        try:
                            if operators[condition[2]](ticket[condition[0]], condition[1]):
                                continue
                            else:
                                break
                        except TypeError:
                            if operators[condition[2]](dt.datetime.now(), condition[1]):
                                continue
                            else:
                                break
                else:
                    results.append(ticket)
        return results

    def create_report_csv(self):
        # for the weekly csv report
        open_tickets = self.filter_data_condition(["geschlossen", "", "=="])
        filter_date_lower = dt.datetime.today() - dt.timedelta(days=7)
        filter_date_upper = dt.datetime.today() + dt.timedelta(days=1)
        lately_closed_tickets = self.filter_data_condition([["geschlossen", filter_date_lower, ">"], ["geschlossen", filter_date_upper, "<"], ["geschlossen", "", "!="]])
        average_working_time = self.calculate_working_time(dataset=lately_closed_tickets)
        report = {"writing date": dt.date.today(), "open tickets": len(open_tickets), "lately closed tickets": len(lately_closed_tickets), "average time open": average_working_time}
        self.write_data_to_csv(report)
        return

    def create_report_json(self):
        # for report on longtime csv report
        csv_data = self.load_data_from_file(filepath=CSV_REPORT, data_type="report")[0]
        open_tickets = 0
        average_time_open = 0
        for weekly_report in csv_data:
            open_tickets += weekly_report["open tickets"]
            average_time_open += weekly_report["average time open"]
        open_tickets = open_tickets / len(csv_data)
        average_time_open = average_time_open / len(csv_data)
        self.write_data_to_json()

if __name__ == "__main__":
    test = TicketAnalyzer()
    test.all_data = test.load_data_from_file()[0]
    test.create_report_json()
    
    
    # < before date