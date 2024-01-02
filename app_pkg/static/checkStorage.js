$(document).ready(function () {

    // Initialize devices table
    var devices_table = $('#devices').DataTable({
        ajax: "/get_devices",
        columns: [            
            { data: 'name', title:'Nombre' },
            { data: 'ae_title', title: 'AE Title' },
            { data: 'address', title: 'Dirección' }
        ],
        searching: false,
        paging: false,
        ordering: false,
        info: false,
        initComplete: function() {
            
            // Delete PACS entry
            idx = devices_table.column(0).data().toArray().indexOf('PACS')
            devices_table.row(idx).remove().draw()
            
            // Select last selected device
            if (localStorage.getItem('storageDevice') !== null) {
                devices_table.row(localStorage.getItem("storageDevice")).select()
            } else {
                devices_table.row().select()
            }
            initDestinations()
            initMissingTable()
            
        }          
    });

    // Enable select behaviour for device table
    $('#devices tbody').on('click', 'tr', function () {                
        if (!$(this).hasClass('selected')) {                  
            devices_table.rows().deselect()
            devices_table.row($(this)).select()
        }
    });

    // Show today in date selector
    if (localStorage.getItem('storageDateSelector') !== null ) {
        $("#startDate").val(localStorage.getItem("storageStartDate"))
        $("#endDate").val(localStorage.getItem("storageEndDate"))
        $("#" + localStorage.getItem("storageDateSelector")).prop("checked", true)
        if (localStorage.getItem("storageDateSelector") == "day") {
            $('#startDate').prop("disabled", false)
        }
        if (localStorage.getItem("storageDateSelector") == "between") {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", false)
        }

    } else {
        $("#today").prop("checked", true)
        document.getElementById('startDate').valueAsDate = new Date()
        document.getElementById('endDate').valueAsDate = new Date()
    }   

    // Enable/disable date pickers
    $("[name='date']").on('click', function(){

        if ($(this)[0].id == 'day') {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", true)
        }
        else if ($(this)[0].id == 'between') {
            $('#startDate').prop("disabled", false)
            $('#endDate').prop("disabled", false)
        }
        else {
            $('#startDate').prop("disabled", true)
            $('#endDate').prop("disabled", true)
        }
    })

    // Disable progress bar smooth transition
    $('#storageProgress').css({transition: "width 0s ease 0s"})
    
});

// Initialize missing series table
function initMissingTable() {
    
    var devices_table = $('#devices').DataTable()
    var table_studies = $('#missing').DataTable({
        ajax: {
            url: "/empty_table",
            method: "POST",
            data: function() {
                    return JSON.stringify({
                        'dateSelector':$("[name='date']:checked").val(),
                        'startDate': $("#startDate").val(),
                        'endDate': $("#endDate").val(),
                        'device': devices_table.rows({ selected: true }).data()[0].name,
                    })
                },
            contentType: 'application/json',
            dataType: "json"
          },              
        columns: [           
            { data: 'source', title: 'Dispositivo' }, 
            { data: 'PatientName', title: 'Paciente' },
            { data: 'PatientID', title: 'ID' },
            { data: 'StudyDate', title: 'Fecha' , type: 'date'},
            { data: 'SeriesTime', title: 'Hora' },
            { data: 'StudyDescription', title: 'Estudio' },
            { data: 'Modality', title: 'Modalidad' },
            { data: 'SeriesDescription', title: 'Serie' },
            { data: 'SeriesNumber', title: 'Numero' },
            { data: 'ImgsSeries', title: 'Imgs' }
        ],
        order: [[0, 'asc'], [3, 'asc'],[4, 'asc']],
        language: {
            search: 'Buscar',
            url: 'https://cdn.datatables.net/plug-ins/1.11.5/i18n/es-ES.json',
            emptyTable: " ",
            processing: " ",
        },
        processing: true,  
        paging: false,
        scrollY: '500px',
        scrollX: true,
        filter: false,
        select: {
            style: 'os',
            selector: 'td',
            info: false,
        },
        initComplete: function() {
            // Change ajax target
            table_studies.ajax.url('/find_missing_series')
            // Initialize table with data stored locally
            if (localStorage.getItem('storageTable') !== null) {
                data = JSON.parse(localStorage.getItem('storageTable'))
                table_studies.rows.add(data).draw()                
            }
        }
    });

    // Manage the missing series search (form submission)
    $("#find_missing").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();

        // Clear previous result messages
        $(".storageResults").remove()

        // Start interval to monitor status
        var interval = setInterval(updateStatus, 1000);
        
        // Alert if device does not inform the number of images in each series.
        if (devices_table.rows({ selected: true }).data()[0].imgs_series == "Unknown") {
            alert(`El campo imgs_series no ha sido definido para este dispositivo. 
            Se chequeará la existencia de la serie solamente`)
        }
        $('#storageProgress').css("width","0%");
        $('#storageProgress').toggleClass('progress-bar-animated');
        $('#findMissingBtn').prop('disabled', true);

        // Clear table, update ajax url 
        table_studies.clear().draw()

        //Store the query data to be shown after refreshing the page
        sourceDevice = devices_table.rows({ selected: true })[0]
        dateSelector = $("[name='date']:checked").prop('id')
        startDate = $("#startDate").val()
        endDate = $("#endDate").val()

        // Retrieve new data      
        table_studies.ajax.reload(function(data) {
            // Stop refreshing and update aspect
            clearInterval(interval)
            $('#storageProgress').css("width","100%")            
            $('#storageStatus').text(" ")
            $('#storageProgress').toggleClass('progress-bar-animated')
            $('#findMissingBtn').prop('disabled', false);

            // Show results message
            console.log(data.series_in_device)
            console.log(data.missing_series)
            console.log(data.filtered_series)
            
            var message = $(`<div class="col storageResults">
                                <div class="alert alert-info alert-dismissible fade show">
                                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                                    <strong>${data.device}:</strong>
                                    <br>
                                    ${data.series_in_device} series en el dispositivo.
                                    ${data.missing_series} series faltantes en el PACS.
                                    ${data.filtered_series} series filtradas.
                                </div>
                            </div>`)
            var title = $("h1")
            title.parent().append(message)

            // Store query data locally to be shown after refreshing
            localStorage.setItem("storageTable",JSON.stringify(table_studies.rows().data().toArray()))
            localStorage.setItem("storageDevice", sourceDevice)
            localStorage.setItem("storageDateSelector", dateSelector)
            localStorage.setItem("storageStartDate", startDate)
            localStorage.setItem("storageEndDate", endDate)
        })
    });    

    // Add send button behaviour
    $("#sendForm").submit(function(event) {
        // Prevent the form from submitting normally
        event.preventDefault();

        // Get destination device
        var ajax_data = {'destination': $("#destinations").val()}

        // Get selected rows
        ajax_data.items = $('#missing').DataTable().rows( { selected : true }).data().toArray()

        // Send request
        $.ajax({
            url: "/move",
            method: "POST",
            data:   JSON.stringify(ajax_data),
            dataType: "json",
            contentType: "application/json",
            success: function(response) {                
                // Show success message
                alert(response.message)
            },
            error: function(xhr, status, error) {
                // handle error response here
                console.log(xhr.responseText);
            }
            });

    });
}

function initDestinations() {
    // Append PACS
    $('#destinations').append($('<option>', { 'PACS' : 'PACS' }).text('PACS'));
    // Append local device
    $('#destinations').append($('<option>', { 'Local' : 'Local' }).text('Local'));
    var selectValues = $('#devices').DataTable().column(0).data()
    $.each(selectValues, function(key, value) {
        $('#destinations')
             .append($('<option>', { value : value })
             .text(value));
   });
}

// Refresh status
function updateStatus () {
    $.ajax({
        url: "/check_storage_progress",
        method: "GET",
        dataType: "json",
        success: function(response) {                
            // Update state indicator
            $('#storageProgress').css("width",response.data.progress)
            $('#storageStatus').text(response.data.status)
        },
        error: function(xhr, status, error) {
            // handle error response here
            console.log(xhr.responseText);
        }
        });
}

// Escape special characters in html element id (to be usable by jQuery)
function jq( myid ) {  
    return "#" + myid.replace( /(:|\.|\[|\]|,|=|@)/g, "\\$1" ); 
}

// Don't show alerts on ajax errors
$.fn.dataTable.ext.errMode = 'throw';
