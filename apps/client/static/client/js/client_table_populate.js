document.addEventListener("DOMContentLoaded", function () {
  const tableBody = document.getElementById("client-table-body");

  // Check if the client table exists
  if (tableBody) {
    fetch("/api/clients/all/")
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            "Failed to fetch client data: " + response.statusText,
          );
        }
        return response.json();
      })
      .then((data) => {
        tableBody.innerHTML = ""; // Clear any existing content
        data.forEach((client) => {
          const row = `
                        <tr class="client-row"
                            data-name="${client.name}"
                            data-email="${client.email || ""}"
                            data-phone="${client.phone || ""}"
                            data-address="${client.address || ""}"
                            data-account-customer="${client.is_account_customer ? "Yes" : "No"}">
                            <td>${client.name}</td>
                            <td>${client.email || ""}</td>
                            <td>${client.phone || ""}</td>
                            <td>${client.address || ""}</td>
                            <td>${client.is_account_customer ? "Yes" : "No"}</td>
                            <td>
                                <a href="/client/${client.id}/" class="btn btn-sm btn-primary">Edit</a>
                            </td>
                        </tr>
                    `;
          tableBody.insertAdjacentHTML("beforeend", row);
        });
      })
      .catch((error) => {
        console.error("Error loading clients:", error);
        tableBody.innerHTML =
          '<tr><td colspan="6" class="text-center">Error loading clients</td></tr>';
      });
  }
});
