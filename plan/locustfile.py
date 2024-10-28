import random

from locust import FastHttpUser, between, run_single_user, task, tag
from locust.clients import LocustResponse


class RandomBorrower(FastHttpUser):
    abstract = True  # Mark as abstract to avoid task scheduling issues
    wait_time = between(1, 5)  # You can define a wait time between tasks
    host = "https://<your-api>.execute-api.eu-west-1.amazonaws.com"
    headers = {
        "accept": "*/*",
        "origin": f"{host}",
    }

    def on_start(self):
        # Each user will have a different borrower_id when started
        self.borrower_id = random.randint(1, 100000)

    def get_borrower(self, borrower_id):
        return self.client.get(
            f"/borrowers/{borrower_id}", headers=self.headers, name="/borrowers"
        )
    
    def get_library_card(self, library_card_id):
        return self.client.get(
            f"/library-cards/{library_card_id}", headers=self.headers, name="/library-card"
        )

    def get_book(self, book_id):
        return self.client.get(
            f"/books/{book_id}", headers=self.headers, name="/books"
        )

    def get_available_books(self):
        return self.client.get(
            "/books/available/", headers=self.headers, name="/books/available/"
        )

    def loan_book(self, book_id, library_card_id) -> LocustResponse:
        payload = {"library_card_id": library_card_id}
        with self.client.post(
            f"/books/{book_id}/loan",
            headers=self.headers,
            json=payload,
            catch_response=True,
            name="/books/loan",
        ) as response:
            if response.status_code == 409:
                # This is expected status code when book is already loaned
                response.success()
                return response
            else:
                return response

    def get_loans(self, library_card_id):
        return self.client.get(
            f"/loans?library_card_id={library_card_id}",
            headers=self.headers,
            name="/loans",
        )

    def get_loan_details(self, loan_id):
        return self.client.get(
            f"/loans/{loan_id}", headers=self.headers, name="/loans/details"
        )

    def add_review(self, book_id, borrower_id):
        payload = {
            "borrower_id": borrower_id,
            "rating": random.randint(1, 5),
            "comment": "Awesome!",
        }
        return self.client.post(
            f"/books/{book_id}/reviews",
            headers=self.headers,
            json=payload,
            name="/books/reviews",
        )

    def delete_loan(self, loan_id):
        return self.client.delete(
            f"/loans/{loan_id}",
            headers=self.headers,
            name="/loans/delete",
        )


class FullTestCase(RandomBorrower):
    @tag('full_test_case')
    @task()
    def perform_tasks(self):
        borrower_response = self.get_borrower(self.borrower_id).json()
        library_card_id = borrower_response["library_card"]["id"]
        available_books_response = self.get_available_books().json()
        book_id = random.choice(available_books_response)["id"]
        loan_book_response = self.loan_book(book_id, library_card_id)
        if loan_book_response.status_code == 409:
            # Book is already on loan, skip the happy case
            pass
        else:
            # Book loaned, go through the happy case
            loans_response = self.get_loans(library_card_id).json()
            loan = random.choice(loans_response)
            loan_id = loan["id"]
            loan_details_response = self.get_loan_details(loan_id).json()
            book_id = loan_details_response["book_id"]
            add_review_response = self.add_review(book_id, self.borrower_id).json()
            delete_loan_response = self.delete_loan(loan_id)


class SimpleTestCase(RandomBorrower):
    @tag('simple_test_case')
    @task()
    def perform_tasks(self):
        borrower_response = self.get_borrower(self.borrower_id).json()
        library_card_id = borrower_response["library_card"]["id"]
        library_card_response = self.get_library_card(library_card_id).json()
        if len(library_card_response["loans"]) > 0:
            loan = random.choice(library_card_response["loans"])
            loan = self.get_loan_details(loan["id"]).json()
            book = self.get_book(loan["book_id"])


if __name__ == "__main__":
    run_single_user(FullTestCase)
