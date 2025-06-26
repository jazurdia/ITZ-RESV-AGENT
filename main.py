from load_xlsx_to_sqlite import load_reservations_to_sqlite, load_grouped_accounts_to_sqlite, delete_itzana_db, reservations_schema, groupedaccounts_schema
from dotenv import load_dotenv
from agents import Runner
from ItzanaAgents import coordinator_agent, reservations_agent

load_dotenv()

def load_db():

    # Borrando DB. 
    delete_itzana_db()

    reservations_loaded = load_reservations_to_sqlite("data/itzana_reservations.xlsx")
    accounts_loaded = load_grouped_accounts_to_sqlite("data/grouped_accounts.xlsx")

    print(f"Reservaciones cargadas a slqite: {reservations_loaded}")
    print(f"Grupos de cuentas cargadas a sqlite: {accounts_loaded}")

def main():

    # Ejemplo de pregunta del usuario:
    pregunta = "¿Cuál fue el ingreso total según los datos de cuentas agrupadas en 2022?"

    # Ejecutar el agente coordinador con la pregunta:
    resultado = Runner.run_sync(reservations_agent, pregunta)

    # Obtener la respuesta final estructurada:
    respuesta_final = resultado.final_output  # debería ser un objeto response_output
    print(respuesta_final)



if __name__ == "__main__":
    load_db()

    main()

