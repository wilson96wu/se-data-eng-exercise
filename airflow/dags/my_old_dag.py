import logging
from random import randint

from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import (
    BranchPythonOperator,
    PythonOperator,
)

from airflow import DAG

log = logging.getLogger(__name__)


def _training_model():
    return randint(1, 10)


def _choose_best_model(ti):
    accuracies = ti.xcom_pull(
        task_ids=["training_model_a", "training_model_b", "training_model_c"]
    )
    best_accuracy = max(accuracies)
    log.warning("best_accuracy: %s", best_accuracy)
    if best_accuracy > 8:
        return "accurate"
    return "inaccurate"


with DAG("my_old_dag") as dag:
    training_model_a = PythonOperator(
        task_id="training_model_a", python_callable=_training_model
    )

    training_model_b = PythonOperator(
        task_id="training_model_b", python_callable=_training_model
    )

    training_model_c = PythonOperator(
        task_id="training_model_c", python_callable=_training_model
    )

    choose_best_model = BranchPythonOperator(
        task_id="choose_best_model", python_callable=_choose_best_model
    )

    accurate = BashOperator(task_id="accurate", bash_command="echo 'accurate'")

    inaccurate = BashOperator(task_id="inaccurate", bash_command="echo 'inaccurate'")

    (
        [training_model_a, training_model_b, training_model_c]
        >> choose_best_model
        >> [accurate, inaccurate]
    )
