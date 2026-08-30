from airflow.sdk import dag, task


@dag()
def my_dag():
    @task
    def training_model_a():
        return 1

    @task
    def training_model_b():
        return 2

    @task
    def training_model_c():
        return 3

    @task.branch
    def chose_best_model(accuracies):
        accuracy = max(accuracies)
        if accuracy > 2:
            return "accurate"
        return "inaccurate"

    @task.bash
    def accurate():
        return "echo 'accurate'"

    @task.bash
    def inaccurate():
        return "echo 'inaccurate'"

    accuracies = [training_model_a(), training_model_b(), training_model_c()]
    (chose_best_model(accuracies) >> [accurate(), inaccurate()])


my_dag()
