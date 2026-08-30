from random import randint

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator


def _train_model(model_name, boost, run_id=None, templates_dict=None):
    # `run_id` and `templates_dict` are not passed explicitly by op_args/op_kwargs alone -
    # Airflow's determine_kwargs() auto-binds any parameter name that matches a key in the
    # task context (run_id) or was set via the templates_dict= operator argument, as long
    # as the callable declares a parameter with that exact name.
    accuracy = randint(1, 10) + boost
    print(f"model={model_name} run_id={run_id} templates_dict={templates_dict} accuracy={accuracy}")
    return accuracy


with DAG("python_operator_all_params_example", catchup=False) as dag:
    train_model = PythonOperator(
        task_id="train_model",
        python_callable=_train_model,
        # op_args: positional args passed to python_callable, i.e. _train_model("model_a", 3, ...)
        op_args=["model_a", 3],
        # op_kwargs: keyword args passed to python_callable. Values are Jinja-templated
        # (op_kwargs is in template_fields), so "{{ run_id }}" is resolved at task run time.
        op_kwargs={"run_id": "{{ run_id }}"},
        # templates_dict: an arbitrary dict made available inside python_callable via the
        # `templates_dict` kwarg on the callable (if it accepts one) or ti.render_templates().
        # Its values are Jinja-templated just like op_kwargs.
        templates_dict={"logical_date": "{{ ds }}"},
        # templates_exts: extra file extensions that, when a templated field's value looks
        # like a path ending in one of these, tells Airflow to render the FILE'S CONTENTS
        # instead of the string itself. Rarely used; shown here for completeness.
        templates_exts=[".json"],
        # show_return_value_in_logs: set False to keep the function's return value out of
        # task logs (it is still pushed to XCom either way) - useful if it may contain
        # sensitive data.
        show_return_value_in_logs=False,
    )
